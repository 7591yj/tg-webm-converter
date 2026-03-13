import logging
from unittest.mock import MagicMock, patch

import pytest

from tg_webm_converter.converter import ConversionResult, ConversionTask, TgWebMConverter


@pytest.fixture
def converter(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    with patch("shutil.which", return_value="/usr/bin/tool"):
        yield TgWebMConverter(str(output_dir))


def test_init_checks_custom_dependency_commands(tmp_path):
    output_dir = tmp_path / "nested" / "output"

    with patch("shutil.which") as which_mock:
        which_mock.return_value = None

        with pytest.raises(FileNotFoundError, match="custom-ffmpeg"):
            TgWebMConverter(
                str(output_dir),
                ffmpeg_command="custom-ffmpeg",
                ffprobe_command="custom-ffprobe",
            )

    assert [call.args[0] for call in which_mock.call_args_list] == ["custom-ffmpeg"]


def test_run_command_logs_failures(converter, caplog):
    with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="boom")):
        with caplog.at_level(logging.ERROR):
            assert converter._run_command(["ffmpeg", "-version"]) is False

    assert "Command failed: ffmpeg -version" in caplog.text
    assert "Stderr: boom" in caplog.text


def test_run_command_returns_true_on_success(converter):
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        assert converter._run_command(["ffmpeg", "-version"]) is True


def test_run_command_handles_missing_binary(converter, caplog):
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with caplog.at_level(logging.ERROR):
            assert converter._run_command(["missing-cmd"]) is False

    assert "Command not found: missing-cmd" in caplog.text


def test_run_command_handles_unexpected_errors(converter, caplog):
    with patch("subprocess.run", side_effect=RuntimeError("bad things")):
        with caplog.at_level(logging.ERROR):
            assert converter._run_command(["ffmpeg"]) is False

    assert "An unexpected error occurred while running command: bad things" in caplog.text


def test_reduce_file_size_returns_early_for_small_files(converter, tmp_path):
    output_path = tmp_path / "small.webm"
    output_path.write_bytes(b"x" * 1024)

    with patch.object(converter, "_run_command") as run_mock:
        assert (
            converter._reduce_file_size(
                output_path,
                TgWebMConverter.ICON_MAX_SIZE,
                bitrate="96K",
                crf="45",
            )
            is True
        )

    run_mock.assert_not_called()


def test_reduce_file_size_reencodes_large_files(converter, tmp_path):
    output_path = tmp_path / "large.webm"
    output_path.write_bytes(b"x" * 50000)
    temp_output = tmp_path / "large.tmp.webm"

    def fake_run_command(args):
        temp_output.write_bytes(b"y" * 20000)
        return True

    with patch.object(converter, "_run_command", side_effect=fake_run_command) as run_mock:
        assert (
            converter._reduce_file_size(
                output_path,
                TgWebMConverter.ICON_MAX_SIZE,
                bitrate="96K",
                crf="45",
            )
            is True
        )

    assert output_path.stat().st_size == 20000
    assert "libvpx-vp9" in run_mock.call_args.args[0]
    assert "96K" in run_mock.call_args.args[0]
    assert "45" in run_mock.call_args.args[0]


def test_reduce_file_size_removes_temp_output_on_failure(converter, tmp_path):
    output_path = tmp_path / "large.webm"
    output_path.write_bytes(b"x" * 50000)
    temp_output = tmp_path / "large.tmp.webm"
    temp_output.write_bytes(b"stale")

    with patch.object(converter, "_run_command", return_value=False):
        assert (
            converter._reduce_file_size(
                output_path,
                TgWebMConverter.ICON_MAX_SIZE,
                bitrate="96K",
                crf="45",
            )
            is False
        )

    assert temp_output.exists() is False


def test_reduce_file_size_warns_when_output_is_still_too_large(
    converter, tmp_path, caplog
):
    output_path = tmp_path / "large.webm"
    output_path.write_bytes(b"x" * 50000)
    temp_output = tmp_path / "large.tmp.webm"

    def fake_run_command(args):
        temp_output.write_bytes(b"y" * 40000)
        return True

    with patch.object(converter, "_run_command", side_effect=fake_run_command):
        with caplog.at_level(logging.WARNING):
            assert (
                converter._reduce_file_size(
                    output_path,
                    TgWebMConverter.ICON_MAX_SIZE,
                    bitrate="96K",
                    crf="45",
                )
                is True
            )

    assert "Could not reduce large.webm below 32KB" in caplog.text


def test_find_supported_files_is_case_insensitive(converter, tmp_path):
    (tmp_path / "one.PNG").write_bytes(b"img")
    (tmp_path / "two.mp4").write_bytes(b"video")
    (tmp_path / "three.webm").write_bytes(b"video")
    (tmp_path / "three.txt").write_text("x")

    files = converter.find_supported_files(str(tmp_path))

    assert files == [
        tmp_path / "one.PNG",
        tmp_path / "three.webm",
        tmp_path / "two.mp4",
    ]


def test_convert_file_rejects_unsupported_input(converter, tmp_path):
    input_path = tmp_path / "notes.txt"
    input_path.write_text("hello")

    result = converter.convert_file(str(input_path), "icon", asset_id="asset-1")

    assert result == ConversionResult(
        asset_id="asset-1",
        source_path=str(input_path.resolve()),
        mode="icon",
        success=False,
        error=f"Unsupported input file: {input_path.resolve()}",
    )


def test_convert_file_returns_structured_failure_for_missing_file(
    converter, tmp_path
):
    result = converter.convert_file(
        str(tmp_path / "missing.png"),
        "icon",
        asset_id="asset-1",
    )

    assert result == ConversionResult(
        asset_id="asset-1",
        source_path=str((tmp_path / "missing.png").resolve()),
        mode="icon",
        success=False,
        error=f"Input file not found: {(tmp_path / 'missing.png').resolve()}",
    )


def test_convert_file_rejects_unknown_mode(converter, tmp_path):
    input_path = tmp_path / "sample.png"
    input_path.write_bytes(b"img")

    result = converter.convert_file(str(input_path), "preview", asset_id="asset-1")

    assert result == ConversionResult(
        asset_id="asset-1",
        source_path=str(input_path.resolve()),
        mode="preview",
        success=False,
        error="Unsupported conversion mode: preview",
    )


def test_convert_file_returns_structured_success_for_icon(converter, tmp_path):
    input_path = tmp_path / "icon.png"
    input_path.write_bytes(b"img")
    output_path = converter.output_dir / "icon.webm"
    output_path.write_bytes(b"x" * 128)

    with patch.object(
        converter, "_run_command", return_value=True
    ) as run_mock, patch.object(converter, "_reduce_file_size", return_value=True):
        result = converter.convert_file(
            str(input_path),
            "icon",
            output_filename="icon.webm",
            asset_id="asset-1",
        )

    assert result.success is True
    assert result.asset_id == "asset-1"
    assert result.output_path == str(output_path)
    assert result.size_bytes == 128
    assert "scale='min(100,iw)':'min(100,ih)':flags=lanczos" in " ".join(
        run_mock.call_args.args[0]
    )
    assert "pad=100:100:(ow-iw)/2:(oh-ih)/2:color=0x00000000,fps=30" in " ".join(
        run_mock.call_args.args[0]
    )


def test_convert_file_accepts_webm_input_for_sticker(converter, tmp_path):
    input_path = tmp_path / "sticker.webm"
    input_path.write_bytes(b"video")
    output_path = converter.output_dir / "sticker.webm"
    output_path.write_bytes(b"x" * 128)

    with patch.object(
        converter, "_run_command", return_value=True
    ) as run_mock, patch.object(converter, "_reduce_file_size", return_value=True):
        result = converter.convert_file(
            str(input_path),
            "sticker",
            output_filename="sticker.webm",
            asset_id="asset-1",
        )

    assert result.success is True
    assert result.asset_id == "asset-1"
    assert result.output_path == str(output_path)
    assert run_mock.called is True


def test_convert_file_returns_icon_failure_when_ffmpeg_fails(converter, tmp_path):
    input_path = tmp_path / "icon.png"
    input_path.write_bytes(b"img")

    with patch.object(
        converter, "_run_command", return_value=False
    ) as run_mock, patch.object(converter, "_reduce_file_size") as reduce_mock:
        result = converter.convert_file(str(input_path), "icon", asset_id="asset-1")

    assert result == ConversionResult(
        asset_id="asset-1",
        source_path=str(input_path.resolve()),
        mode="icon",
        success=False,
        error="ffmpeg failed during icon conversion",
    )
    run_mock.assert_called_once()
    reduce_mock.assert_not_called()


def test_convert_file_returns_icon_failure_when_reduction_fails(converter, tmp_path):
    input_path = tmp_path / "icon.png"
    input_path.write_bytes(b"img")

    with patch.object(
        converter, "_run_command", return_value=True
    ), patch.object(converter, "_reduce_file_size", return_value=False):
        result = converter.convert_file(str(input_path), "icon", asset_id="asset-1")

    assert result == ConversionResult(
        asset_id="asset-1",
        source_path=str(input_path.resolve()),
        mode="icon",
        success=False,
        error="Failed to reduce icon file size",
    )


def test_convert_file_returns_structured_success_for_sticker(
    converter, tmp_path
):
    input_path = tmp_path / "sample.png"
    input_path.write_bytes(b"img")
    output_path = converter.output_dir / "sample.webm"
    output_path.write_bytes(b"x" * 256)

    with patch.object(
        converter, "_run_command", return_value=True
    ) as run_mock, patch.object(
        converter, "_reduce_file_size", return_value=True
    ):
        result = converter.convert_file(str(input_path), "sticker", asset_id="asset-1")

    assert result.success is True
    assert result.output_path == str(output_path)
    assert (
        "scale='if(gte(iw,ih),512,-1)':'if(gte(iw,ih),-1,512)':flags=lanczos,"
        "fps=30"
    ) in run_mock.call_args.args[0]


def test_convert_file_returns_sticker_failure_when_ffmpeg_fails(converter, tmp_path):
    input_path = tmp_path / "sample.png"
    input_path.write_bytes(b"img")

    with patch.object(
        converter, "_run_command", return_value=False
    ), patch.object(
        converter, "_reduce_file_size"
    ) as reduce_mock:
        result = converter.convert_file(str(input_path), "sticker", asset_id="asset-1")

    assert result == ConversionResult(
        asset_id="asset-1",
        source_path=str(input_path.resolve()),
        mode="sticker",
        success=False,
        error="ffmpeg failed during sticker conversion",
    )
    reduce_mock.assert_not_called()


def test_convert_file_returns_sticker_failure_when_reduction_fails(
    converter, tmp_path
):
    input_path = tmp_path / "sample.png"
    input_path.write_bytes(b"img")

    with patch.object(
        converter, "_run_command", return_value=True
    ), patch.object(
        converter, "_reduce_file_size", return_value=False
    ):
        result = converter.convert_file(str(input_path), "sticker", asset_id="asset-1")

    assert result == ConversionResult(
        asset_id="asset-1",
        source_path=str(input_path.resolve()),
        mode="sticker",
        success=False,
        error="Failed to reduce sticker file size",
    )


def test_convert_tasks_supports_output_overrides(converter, tmp_path):
    input_path = tmp_path / "sample.png"
    input_path.write_bytes(b"img")
    output_path = converter.output_dir / "custom.webm"
    output_path.write_bytes(b"x" * 32)

    with patch.object(
        converter, "_run_command", return_value=True
    ), patch.object(converter, "_reduce_file_size", return_value=True):
        results = converter.convert_tasks(
            [
                ConversionTask(
                    asset_id="asset-2", source_path=str(input_path), mode="icon"
                )
            ],
            output_name_overrides={"asset-2": "custom.webm"},
        )

    assert len(results) == 1
    assert results[0].output_path == str(output_path)


def test_convert_to_icon_wrapper_returns_boolean(converter):
    with patch.object(
        converter,
        "convert_file",
        return_value=ConversionResult(
            asset_id=None,
            source_path="/tmp/icon.png",
            mode="icon",
            success=True,
        ),
    ) as convert_file_mock:
        assert converter.convert_to_icon("/tmp/icon.png") is True

    convert_file_mock.assert_called_once_with("/tmp/icon.png", "icon")


def test_convert_to_sticker_wrapper_returns_boolean(converter):
    with patch.object(
        converter,
        "convert_file",
        return_value=ConversionResult(
            asset_id=None,
            source_path="/tmp/icon.png",
            mode="sticker",
            success=False,
            error="failed",
        ),
    ) as convert_file_mock:
        assert converter.convert_to_sticker("/tmp/icon.png") is False

    convert_file_mock.assert_called_once_with("/tmp/icon.png", "sticker")
