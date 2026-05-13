import re


_DIFF_HEADER = re.compile(r"^(---|\+\+\+|@@)", re.MULTILINE)
_HUNK_HEADER = re.compile(r"^@@\s+-\d+", re.MULTILINE)


def validate_patch(patch: str) -> tuple[bool, str]:
    if not patch or not patch.strip():
        return False, "Patch is empty."
    if not _DIFF_HEADER.search(patch):
        return False, "Patch does not contain unified diff headers (---, +++, @@)."
    if not _HUNK_HEADER.search(patch):
        return False, "Patch contains no hunk headers (@@)."
    return True, ""
