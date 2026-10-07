"""
Model utility functions for MAPS.
"""

from pathlib import Path
from typing import Union

LFS_HEADER = b"version https://git-lfs.github.com/spec/v1"


def is_lfs_pointer(path: Union[str, Path, None]) -> bool:
    """
    Check whether a file path points to a Git LFS pointer text file instead of real binary data.

    Returns True when the file exists, is under 1024 bytes, and starts with
    b"version https://git-lfs.github.com/spec/v1".
    Returns False otherwise (including for missing, unreadable, or non-pointer files).
    """
    if path is None:
        return False
    try:
        p = Path(path)
        if not p.is_file():
            return False
        if p.stat().st_size >= 1024:
            return False
        with open(p, "rb") as f:
            header = f.read(len(LFS_HEADER))
            return header == LFS_HEADER
    except Exception:
        return False
