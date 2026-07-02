import argparse
import json
import sys
from typing import List, Dict, Tuple, Optional

from csf import CSF
from csfpatch import CSFPatch, CSFPatchException


def get_cmdline_data() -> Tuple[bool, str, List[str]]:
    parser = argparse.ArgumentParser()
    parser.add_argument("-V", "--version", action="version", version="%(prog)s 1.0.0")
    parser.add_argument("-r", "--russian-lang", action="store_true",
                        help="Enables decoding of Russian localisation, which uses Windows-1251 encoding.")
    parser.add_argument("action", action="store", choices=["decompile", "compile", "patch", "lookup"],
                        help="What to do.")
    parser.add_argument("params", action="store", nargs="*")
    args = parser.parse_args()
    return args.russian_lang, args.action, args.params


def load_csf(path: str, quirk: bool) -> Optional[CSF]:
    print(f'Loading CSF "{path}"...')
    try:
        data = CSF.from_csf(path, quirk)
        print(f'Loaded CSF "{path}" [{data.get_language_string()}, {data.total_strings} strings in '
              f'{data.total_entries} entries].')
        return data
    except Exception as ex:
        print(f'Failed to open CSF file "{path}" - {ex}')
        return None


def act_compile(params: List[str], quirk: bool):
    if len(params) != 2:
        return 2
    targetfile, sourcefile = params
    if quirk:
        print("Russian language mode: reading strings in Windows-1251 encoding.")
    print(f'Loading CSF data from "{sourcefile}"...')
    try:
        data = CSF.from_json(sourcefile)
    except Exception as ex:
        print(f'Failed to open CSF data file "{sourcefile}" - {ex}')
        return 1
    print(f'Compiling new csf file "{targetfile}"...')
    data.save_csf(targetfile, quirk)
    print("Done")
    return 0


def act_decompile(params: List[str], quirk: bool):
    if quirk:
        print("Russian language mode: reading strings in Windows-1251 encoding.")
    for file in params:
        try:
            data = CSF.from_csf(file, quirk)
            data.save_json(file + ".json")
        except Exception as ex:
            print(f'Skipping file "{file}" - {ex}.')
    return 0


def act_lookup(params: List[str], quirk: bool):
    if len(params) < 2:
        return 2
    sourcefile = params[0]
    data = load_csf(sourcefile, quirk)
    if data is None:
        return 1
    add_break = False
    for entry in params[1:]:
        strings = data.entry_lookup(entry)
        if strings:
            if add_break:
                print()
            print(f"{entry}:")
            for s in strings:
                print(json.dumps(s, ensure_ascii=False))
            add_break = True
    return 0


def act_patch(params: List[str], quirk: bool) -> int:
    if len(params) < 2:
        return 2
    targetfile = params[0]
    data = load_csf(targetfile, quirk)
    if data is None:
        return 1
    final_patch: Optional[CSFPatch] = None
    print(f'Loading patches...')
    for file in params:
        try:
            current_patch = CSFPatch.from_json(file)
            print(f'Loaded patch "{current_patch.description}" [{file}].')
            if final_patch is None:
                final_patch = current_patch
            else:
                final_patch.merge_patch(current_patch)
        except KeyError:
            print(f"Skipping patch file '{file}' - patch file is invalid or corrupt.")
        except UnicodeDecodeError:
            print(f"Skipping patch file '{file}' - Not a patch file.")
        except (json.JSONDecodeError, CSFPatchException) as ex:
            print(f"Skipping patch file '{file}' - {ex}.")
    if final_patch is None or final_patch.is_empty():
        print(f'There are no changes to apply.')
    else:
        print(f'Applying resulting patch...')
        final_patch.apply(data)
        data.save_csf(targetfile, quirk)
        print(f'Done')
    return 0


def main():
    actions: Dict[str, Tuple] = {
        "compile": (act_compile, "where_to_write, json_file_with_csf_data"),
        "decompile": (act_decompile, "file_to_decompile[, ...]"),
        "lookup": (act_lookup, "csf_file, stringkey_to_find[, ...]"),
        "patch": (act_patch, "csf_file_to_patch, csf_patch1.json[, ...]")
    }
    quirk, action, params = get_cmdline_data()
    if action not in actions:
        print(f'Unknown action "{action}". Supported actions:')
        for k in actions:
            print(k)
        return 1
    result = actions[action][0](params, quirk)
    if result == 2:
        print(f'Usage:\n{sys.argv[0]} {action} {actions[action][1]}')
    return result


if __name__ == "__main__":
    sys.exit(main())
