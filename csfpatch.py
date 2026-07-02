import json
from typing import List, Dict, Set, Optional

from csf import CSF, CSFEntryName


class CSFPatchException(Exception):
    pass


class CSFPatch:
    def __init__(self, additions: Dict[CSFEntryName, List[Dict[str, Optional[str]]]],
                 assignments: Dict[CSFEntryName, List[Dict[str, Optional[str]]]],
                 removals: Set[CSFEntryName], description: str):
        self._additions = additions
        self._assignments = assignments
        self._removals = removals
        self._desc = description

    @property
    def additions(self) -> Dict[CSFEntryName, List[Dict[str, Optional[str]]]]:
        return self._additions.copy()

    def apply(self, csf: CSF):
        for csfkey in self._removals:
            csf.entry_delete(csfkey)
        for csfkey, values in self._assignments.items():
            csf.entry_set_strings(csfkey, values)
        for csfkey, values in self._additions.items():
            csf.entry_add_strings(csfkey, values)

    @property
    def description(self):
        return self._desc

    def merge_patch(self, incoming_patch: "CSFPatch"):
        for csfkey in incoming_patch._removals:
            self._additions.pop(csfkey, None)
            self._assignments.pop(csfkey, None)
            self._removals.add(csfkey)
        for csfkey, value in incoming_patch._assignments.items():
            self._additions.pop(csfkey, None)
            self._removals.discard(csfkey)
            self._assignments[csfkey] = value
        for csfkey, value in incoming_patch._additions.items():
            if csfkey in self._additions:
                self._additions[csfkey].extend(value)
            else:
                self._additions[csfkey] = value

    @classmethod
    def from_json(cls, file: str):
        result = {
            "add": {},
            "set": {},
        }
        with open(file, "r", encoding="utf-8") as patchfile:
            patch: dict = json.load(patchfile)
            if patch.get("type") != "csf_patch":
                raise CSFPatchException("Not a patch file")
            if patch.get("format_version") != 1:
                raise CSFPatchException("Unsupported patch version.")
            desc = patch["description"]
            affected_keys = {}
            deleted_keys = set()
            for key in patch.get("del", []):
                csfkey = CSFEntryName(key)
                deleted_keys.add(csfkey)
                affected_keys[csfkey] = "del"
            for action in {"add", "set"}:
                for key, value in patch.get(action, {}).items():
                    csfkey = CSFEntryName(key)
                    if csfkey in affected_keys:
                        raise CSFPatchException(
                            f'{file}: Actions "{action}" and "{affected_keys[csfkey]}" affect the same '
                            f'key "{csfkey}" in the patch.')
                    result[action][csfkey] = value
                    affected_keys[csfkey] = action
        return cls(result["add"], result["set"], deleted_keys, desc)

    def is_empty(self) -> bool:
        return len(self._additions) + len(self.removals) + len(self.replacements) == 0

    @property
    def replacements(self) -> Dict[CSFEntryName, List[Dict[str, Optional[str]]]]:
        return self._assignments.copy()

    @property
    def removals(self) -> Set[CSFEntryName]:
        return self._removals.copy()
