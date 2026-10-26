"""Keep encoding stages outside the user-visible output folder."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path


def create_video_work_paths(output_dir: str | os.PathLike, intermediate_name: str):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    work_root = output_dir / ".video_work"
    work_root.mkdir(exist_ok=True)
    _remove_stale_workdirs(work_root)
    work_dir = Path(tempfile.mkdtemp(prefix="job_", dir=str(work_root)))
    final_name = intermediate_name[:-len("_0.mp4")] + ".mp4" if intermediate_name.endswith("_0.mp4") else intermediate_name
    return str(work_dir / intermediate_name), str(output_dir / final_name), work_dir


def cleanup_video_work(work_dir: str | os.PathLike | None) -> None:
    if not work_dir:
        return
    path = Path(work_dir)
    try:
        if path.is_dir() and path.parent.name == ".video_work":
            shutil.rmtree(path)
            try:
                path.parent.rmdir()
            except OSError:
                pass
    except OSError:
        pass


def _remove_stale_workdirs(work_root: Path) -> None:
    cutoff = time.time() - 24 * 60 * 60
    try:
        for path in work_root.glob("job_*"):
            try:
                if path.is_dir() and path.stat().st_mtime < cutoff:
                    shutil.rmtree(path)
            except OSError:
                continue
    except OSError:
        pass
