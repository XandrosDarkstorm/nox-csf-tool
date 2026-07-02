import json
from typing import List, Dict, Optional

import binreader

languages = {
        0: "English",
        1: "Spanish",
        2: "German",
        6: "Italian",
        7: "Dutch",
        9: "Swedish",
        10: "Chinese",
        13: "Norwegian / Thai",
        17: "Russian"
    }


class CSFException(Exception):
    pass


class CSFEntryName:
    def __init__(self, value: str):
        self._value = value
        self._canonical_value = value.casefold()
        self._hash = hash(self._canonical_value)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        if isinstance(other, CSFEntryName):
            return self._canonical_value == other._canonical_value
        return NotImplemented

    def __str__(self):
        return self._value

    def __repr__(self):
        return f"EntryKey({self._canonical_value})"


MAGIC = b" FSC"
LBL = b" LBL"
STR = b" rtS"
STRW = b"WrtS"


class CSF:
    def __init__(self, entries: Dict[CSFEntryName, List[Dict[str, Optional[str]]]],
                 total_entries: int, total_strings: int, language_index: int):
        self._entries = entries
        self._total_entries = total_entries
        self._total_strings = total_strings
        self._language_index = language_index

    @classmethod
    def from_csf(cls, path: str, ansimode: bool):
        with binreader.BinReader(path) as f:
            if f.read_bytes(4) != MAGIC:
                raise CSFException("Not a CSF!")
            if f.read_uint32() != 2:
                raise CSFException("Only v2 format is supported (NOX)")
            total_records = f.read_uint32()
            total_strings = f.read_uint32()
            f.skip(4)  # Gap
            language_index = f.read_uint32()
            entries = {}
            for _ in range(total_records):
                # " LBL" block
                blockname = f.read_bytes(4).decode("utf-8").upper()
                if blockname != " LBL":
                    raise CSFException(f"Unexpected block '{blockname}' at position {f.tell() - 4}.")
                strings_to_read = f.read_uint32()
                size = f.read_uint32()
                key = f.read_bytes(size).decode("ascii")
                strings = []
                for _2 in range(strings_to_read):
                    blockname = f.read_bytes(4).decode("utf-8").upper()
                    if blockname not in {" RTS", "WRTS"}:
                        raise CSFException(f"Unexpected block '{blockname}' inside the label at "
                                           f"position {f.tell() - 4}.")
                    # String block
                    length = f.read_uint32()
                    raw = f.read_bytes(length * 2)  # 2-byte encoding is used
                    if ansimode:  # Is ANSI-encoded
                        decrypted = bytearray([c ^ 0xFF for c in raw if c != 0xFF])
                        value = decrypted.decode("windows-1251")
                    else:
                        decrypted = bytearray([c ^ 0xFF for c in raw])
                        value = decrypted.decode("utf-16-le")
                    sound = None
                    if blockname == "WRTS":
                        sound = f.read_bytes(f.read_uint32()).decode("utf-8")
                    strings.append({"sound": sound, "value": value})
                entries[CSFEntryName(key)] = strings
            return cls(entries, total_records, total_strings, language_index)

    @classmethod
    def from_json(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("type") != "csf_data":
            raise CSFException("Not a valid JSON dump of CSF data")
        try:
            language_index: int = data["language_index"]
            total_entries: int = len(data["entries"])
            total_strings = 0
            entries: Dict[CSFEntryName, List[Dict]] = {}
            while data["entries"]:
                key = next(iter(data["entries"]))
                value = data["entries"].pop(key)
                total_strings += len(value)
                entries[CSFEntryName(key)] = value
        except KeyError:
            raise CSFException("Not a valid JSON dump of CSF data")
        return cls(entries, total_entries, total_strings, language_index)

    def entry_add_strings(self, key: CSFEntryName, value: List[Dict[str, Optional[str]]]):
        entry = self._entries.get(key)
        self._total_strings += len(value)
        if entry is None:
            self._entries[key] = value.copy()
            self._total_entries += 1
        else:
            entry.extend(value)

    def entry_delete(self, key: CSFEntryName):
        value = self._entries.pop(key, None)
        if value is not None:
            self._total_entries -= 1
            self._total_strings -= len(value)

    def entry_lookup(self, key: str):
        return self._entries.get(CSFEntryName(key))

    def entry_set_strings(self, key: CSFEntryName, value: List[Dict[str, Optional[str]]]):
        entryval = self._entries.get(key)
        if entryval is None:
            self._total_entries += 1
        else:
            self._total_strings -= len(entryval)
        self._entries[key] = value.copy()
        self._total_strings += len(value)

    def get_language_string(self) -> str:
        return languages.get(self._language_index, f"Unknown language {self._language_index}")

    @property
    def language_index(self):
        return self._language_index

    def _jsonval(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)

    def save_json(self, path: str):
        result = f'{{\n"type": "csf_data",\n"language_index": {self._language_index},\n"entries": {{\n\n\n'
        for key, values in self._entries.items():
            result += f'{self._jsonval(str(key))}: [\n'
            total_values = len(values)
            processed_strings = 0
            for entry in values:
                result += f'{{"sound": {self._jsonval(entry["sound"])}, "value": {self._jsonval(entry["value"])}}}'
                processed_strings += 1
                if processed_strings != total_values:
                    result += ",\n"
            result += "\n],\n\n"
        result = result[:-3] + "\n}\n}"
        with open(path, "w", encoding="utf-8") as outfile:
            outfile.write(result)

    def save_csf(self, path: str, ansimode: bool):
        with open(path, "wb") as outfile:
            outfile.write(MAGIC)
            outfile.write(int(2).to_bytes(4, "little"))
            outfile.write(self._total_entries.to_bytes(4, "little"))
            outfile.write(self._total_strings.to_bytes(4, "little"))
            outfile.write(int(0).to_bytes(4, "little"))
            outfile.write(self._language_index.to_bytes(4, "little"))
            for key, strings in self._entries.items():
                outfile.write(LBL)
                outfile.write(len(strings).to_bytes(4, "little"))
                outfile.write(len(str(key)).to_bytes(4, "little"))
                outfile.write(str(key).encode("ascii"))
                for string in strings:
                    sound: Optional[str] = string["sound"]
                    # noinspection PyTypeChecker
                    value: str = string["value"]
                    outfile.write(STR if sound is None else STRW)
                    outfile.write(len(value).to_bytes(4, "little"))
                    if ansimode:
                        encodedstr = value.encode("windows-1251")
                        buffer = bytearray(len(encodedstr) * 2)
                        buffer[0::2] = encodedstr
                        buffer = bytes(buffer)
                    else:
                        buffer = value.encode("utf-16-le")
                    for b in buffer:
                        outfile.write(int(b ^ 0xFF).to_bytes(1, "little"))
                    if sound is not None:
                        outfile.write(len(sound).to_bytes(4, "little"))
                        outfile.write(sound.encode("utf-8"))

    @property
    def total_entries(self):
        return self._total_entries

    @property
    def total_strings(self):
        return self._total_strings
