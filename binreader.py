import io
import os.path


class BinReader:
    def __init__(self, filepath):
        self._file = None
        if not os.path.isfile(filepath):
            raise FileNotFoundError(filepath)
        self._file = open(filepath, "rb")

    def tell(self) -> int:
        if self._file is None:
            raise RuntimeError("File is not opened.")
        return self._file.tell()

    def skip(self, amount: int):
        if self._file is None:
            raise RuntimeError("File is not opened.")
        self._file.seek(amount, io.SEEK_CUR)

    def read_bytes(self, amount: int) -> bytes:
        if self._file is None:
            raise RuntimeError("File is not opened.")
        result = self._file.read(amount)
        resultlen = len(result)
        if resultlen != amount:
            self._file.seek(-resultlen, io.SEEK_CUR)
            raise EOFError(f"Attempted to read past EOF ({amount} requested, {resultlen} was available).")
        return result

    def _read_integer(self, size: int, signed: bool):
        try:
            return int.from_bytes(self.read_bytes(size), byteorder="little", signed=signed)
        except ValueError:
            self._file.seek(-size, io.SEEK_CUR)
            raise

    def read_uint32(self) -> int:
        return self._read_integer(4, False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return None

    def __del__(self):
        self.close()

    def close(self):
        if self._file is not None:
            self._file.close()
