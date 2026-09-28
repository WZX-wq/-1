import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors="replace")
    except Exception:
        pass

from PyQt6.QtWidgets import QApplication

import main
from database_tool.material_download_tool import get_last_material_download_error


LOG_DIR = ROOT / "diagnostics"
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / f"auto_generate_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
_log_lock = threading.Lock()


def record(event, **data):
    payload = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        **data,
    }
    line = json.dumps(payload, ensure_ascii=False, default=str)
    with _log_lock:
        with LOG_PATH.open("a", encoding="utf-8") as file_obj:
            file_obj.write(line + "\n")
    print(line, flush=True)


def wrap_download(name):
    original = getattr(main, name)

    def wrapped(*args, **kwargs):
        started = time.monotonic()
        try:
            result = original(*args, **kwargs)
            record(
                name,
                arguments=args,
                success=bool(result and os.path.exists(result)),
                result=result,
                error=get_last_material_download_error(),
                elapsed=round(time.monotonic() - started, 3),
            )
            return result
        except Exception as error:
            record(
                name,
                arguments=args,
                success=False,
                exception=repr(error),
                error=get_last_material_download_error(),
                elapsed=round(time.monotonic() - started, 3),
            )
            raise

    setattr(main, name, wrapped)


def wrap_query(name):
    original = getattr(main, name)

    def wrapped(*args, **kwargs):
        started = time.monotonic()
        result = original(*args, **kwargs)
        ids = [item.get("id") for item in result] if isinstance(result, list) else []
        record(
            name,
            arguments=args,
            result_count=len(result) if isinstance(result, list) else None,
            ids=ids,
            elapsed=round(time.monotonic() - started, 3),
        )
        return result

    setattr(main, name, wrapped)


def wrap_title_query():
    original = main.get_title_info_by_type

    def wrapped(account_name, title_type):
        result = original(account_name, title_type)
        record(
            "title_selected",
            account=account_name,
            requested_type=title_type,
            title_id=result[0] if result else None,
            title=result[1] if result else None,
            actual_type=result[6] if result else None,
        )
        return result

    main.get_title_info_by_type = wrapped


def run():
    for name in (
        "download_cover_video",
        "download_video",
        "download_cn_video",
        "download_afr_video",
    ):
        wrap_download(name)
    for name in ("get_videos_by_keyword", "get_videos_by_keyword_1"):
        wrap_query(name)
    wrap_title_query()

    main.setup_ffmpeg_path()
    app = QApplication.instance() or QApplication([])
    window = main.BatchAICutter()
    original_add_log = window.add_log

    def diagnostic_add_log(message):
        record("ui_log", message=message)
        return original_add_log(message)

    window.add_log = diagnostic_add_log
    window.compositeTimeSpinBox.setValue(10)
    window.uploadCheckBox.setChecked(False)

    record("run_start", requested_videos=10, upload=False, log_path=str(LOG_PATH))
    try:
        window.auto_generate()
    except Exception as error:
        record("run_crashed", exception=repr(error))
        raise
    finally:
        record("run_finished")
        window.close()
        app.quit()


if __name__ == "__main__":
    run()
