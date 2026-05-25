import json
import os
import sys
from pathlib import Path
from typing import Dict, List

from tg_webm_converter.converter import TgWebMConverter


def _emit(event: Dict) -> None:
    print(json.dumps(event), flush=True)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_task_output_path(task: Dict, output_root: Path) -> Path:
    output_path = Path(task["outputPath"]).resolve()
    if not _is_relative_to(output_path, output_root):
        raise ValueError(
            f"Task outputPath must be inside outputRoot: {output_path}"
        )
    return output_path


def _task_sticker_id(task: Dict) -> str:
    return task["stickerId"]


def run_from_request(payload: Dict) -> int:
    output_root = Path(payload["outputRoot"]).resolve()
    tasks: List[Dict] = payload["tasks"]
    task_output_paths = {
        _task_sticker_id(task): _resolve_task_output_path(task, output_root)
        for task in tasks
    }
    converter = TgWebMConverter(
        str(output_root),
        ffmpeg_command=os.environ.get("STICKER_SMITH_FFMPEG", "ffmpeg"),
        ffprobe_command=os.environ.get("STICKER_SMITH_FFPROBE", "ffprobe"),
    )

    _emit(
        {
            "type": "job_started",
            "jobId": payload["jobId"],
            "taskCount": len(tasks),
        }
    )

    success_count = 0
    failure_count = 0

    for task in tasks:
        _emit(
            {
                "type": "sticker_started",
                "jobId": payload["jobId"],
                "stickerId": _task_sticker_id(task),
                "mode": task["mode"],
            }
        )

        result = converter.convert_file(
            task["sourcePath"],
            task["mode"],
            output_path=str(task_output_paths[_task_sticker_id(task)]),
            asset_id=_task_sticker_id(task),
        )

        if result.success:
            success_count += 1
            _emit(
                {
                    "type": "sticker_completed",
                    "jobId": payload["jobId"],
                    "stickerId": _task_sticker_id(task),
                    "mode": task["mode"],
                    "outputPath": result.output_path,
                    "sizeBytes": result.size_bytes,
                }
            )
        else:
            failure_count += 1
            _emit(
                {
                    "type": "sticker_failed",
                    "jobId": payload["jobId"],
                    "stickerId": _task_sticker_id(task),
                    "mode": task["mode"],
                    "error": result.error,
                }
            )

    _emit(
        {
            "type": "job_finished",
            "jobId": payload["jobId"],
            "successCount": success_count,
            "failureCount": failure_count,
        }
    )

    return 0 if failure_count == 0 else 1


def main() -> int:
    payload = json.load(sys.stdin)
    return run_from_request(payload)


if __name__ == "__main__":
    raise SystemExit(main())
