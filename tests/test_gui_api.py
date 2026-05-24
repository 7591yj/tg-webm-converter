import json
from unittest.mock import MagicMock, patch

import pytest

from tg_webm_converter.gui_api import run_from_request


def test_run_from_request_emits_ndjson_events(capsys, tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"img")

    success_result = MagicMock(
        success=True,
        output_path=str(tmp_path / "icon.webm"),
        size_bytes=42,
    )

    with patch("tg_webm_converter.gui_api.TgWebMConverter") as converter_class:
        converter_class.return_value.convert_file.return_value = success_result

        exit_code = run_from_request(
            {
                "jobId": "job-1",
                "outputRoot": str(tmp_path / "out"),
                "tasks": [
                    {
                        "assetId": "asset-1",
                        "sourcePath": str(image_path),
                        "mode": "icon",
                        "outputPath": str(tmp_path / "out" / "icon.webm"),
                    }
                ],
            }
        )

    assert exit_code == 0
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [event["type"] for event in events] == [
        "job_started",
        "asset_started",
        "asset_completed",
        "job_finished",
    ]
    assert events[2]["outputPath"].endswith("icon.webm")
    converter_class.return_value.convert_file.assert_called_once_with(
        str(image_path),
        "icon",
        output_path=str((tmp_path / "out" / "icon.webm").resolve()),
        asset_id="asset-1",
    )


def test_run_from_request_returns_failure_exit_code(capsys, tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"img")

    failure_result = MagicMock(success=False, error="ffmpeg failed")

    with patch("tg_webm_converter.gui_api.TgWebMConverter") as converter_class:
        converter_class.return_value.convert_file.return_value = failure_result

        exit_code = run_from_request(
            {
                "jobId": "job-1",
                "outputRoot": str(tmp_path / "out"),
                "tasks": [
                    {
                        "assetId": "asset-1",
                        "sourcePath": str(image_path),
                        "mode": "sticker",
                        "outputPath": str(tmp_path / "out" / "asset-1.webm"),
                    }
                ],
            }
        )

    assert exit_code == 1
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[2]["type"] == "asset_failed"
    assert events[-1]["failureCount"] == 1


def test_run_from_request_rejects_output_path_outside_output_root(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"img")

    with pytest.raises(ValueError, match="inside outputRoot"):
        run_from_request(
            {
                "jobId": "job-1",
                "outputRoot": str(tmp_path / "out"),
                "tasks": [
                    {
                        "assetId": "asset-1",
                        "sourcePath": str(image_path),
                        "mode": "sticker",
                        "outputPath": str(tmp_path / "elsewhere" / "asset-1.webm"),
                    }
                ],
            }
        )
