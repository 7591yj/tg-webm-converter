import json
import os
import sys
from pathlib import Path
from typing import Dict, List

from tg_webm_converter.converter import TgWebMConverter


def _emit(event: Dict) -> None:
    print(json.dumps(event), flush=True)


def _build_output_file_name(task: Dict, task_index: int) -> str:
    if task["mode"] == "icon":
        return "icon.webm"

    stem = Path(task["sourcePath"]).stem
    return f"{stem}-{task['assetId'][:8]}-{task_index}.webm"


def run_from_request(payload: Dict) -> int:
    output_root = payload["outputRoot"]
    tasks: List[Dict] = payload["tasks"]
    converter = TgWebMConverter(
        output_root,
        ffmpeg_command=os.environ.get("STICKER_SMITH_FFMPEG", "ffmpeg"),
        ffprobe_command=os.environ.get("STICKER_SMITH_FFPROBE", "ffprobe"),
    )
    overrides = {
        task["assetId"]: _build_output_file_name(task, index)
        for index, task in enumerate(tasks, start=1)
    }

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
                "type": "asset_started",
                "jobId": payload["jobId"],
                "assetId": task["assetId"],
                "mode": task["mode"],
            }
        )

        result = converter.convert_file(
            task["sourcePath"],
            task["mode"],
            output_filename=overrides[task["assetId"]],
            asset_id=task["assetId"],
        )

        if result.success:
            success_count += 1
            _emit(
                {
                    "type": "asset_completed",
                    "jobId": payload["jobId"],
                    "assetId": task["assetId"],
                    "mode": task["mode"],
                    "outputPath": result.output_path,
                    "sizeBytes": result.size_bytes,
                }
            )
        else:
            failure_count += 1
            _emit(
                {
                    "type": "asset_failed",
                    "jobId": payload["jobId"],
                    "assetId": task["assetId"],
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
