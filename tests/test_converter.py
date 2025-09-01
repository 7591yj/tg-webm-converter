from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import logging
import subprocess

# Assuming TgWebMConverter is in tg_webm_converter/converter.py
from tg_webm_converter.converter import TgWebMConverter


@pytest.fixture
def converter(tmp_path):
    """Fixture for a TgWebMConverter instance."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    with patch('shutil.which', return_value="/usr/bin/ffmpeg"):
        yield TgWebMConverter(str(output_dir))


@pytest.fixture
def mock_subprocess_run():
    """Mocks subprocess.run for various scenarios."""
    with patch('subprocess.run') as mock_run:
        yield mock_run


class TestTgWebMConverter:
    """Test cases for TgWebMConverter class."""

    def test_init_creates_output_directory(self, tmp_path):
        """Test that initialization creates output directory."""
        output_dir = tmp_path / "test_output"
        with patch('shutil.which', return_value="/usr/bin/ffmpeg"):
            converter = TgWebMConverter(str(output_dir))

        assert output_dir.exists()
        assert converter.output_dir == output_dir

    def test_init_with_existing_directory(self, tmp_path):
        """Test initialization with existing output directory."""
        output_dir = tmp_path / "existing"
        output_dir.mkdir()

        with patch('shutil.which', return_value="/usr/bin/ffmpeg"):
            converter = TgWebMConverter(str(output_dir))
        assert converter.output_dir == output_dir

    def test_init_checks_dependencies(self, tmp_path):
        """Test that initialization checks for ffmpeg and ffprobe."""
        output_dir = tmp_path / "test_output"
        with patch('shutil.which') as mock_which:
            mock_which.side_effect = [None, "/usr/bin/ffprobe"]  # ffmpeg not found
            with pytest.raises(FileNotFoundError, match="ffmpeg"):
                TgWebMConverter(str(output_dir))

            mock_which.reset_mock()
            mock_which.side_effect = ["/usr/bin/ffmpeg", None]  # ffprobe not found
            with pytest.raises(FileNotFoundError, match="ffprobe"):
                TgWebMConverter(str(output_dir))

            mock_which.reset_mock()
            mock_which.side_effect = ["/usr/bin/ffmpeg", "/usr/bin/ffprobe"]
            TgWebMConverter(str(output_dir))  # Should succeed

    def test_supported_extensions(self):
        """Test that supported extensions are correctly defined."""
        expected_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.mp4'
        ]
        assert TgWebMConverter.SUPPORTED_EXTENSIONS == expected_extensions

    def test_size_limits(self):
        """Test that size limits are correctly defined."""
        assert TgWebMConverter.ICON_MAX_SIZE == 32 * 1024  # 32KB
        assert TgWebMConverter.STICKER_MAX_SIZE == 256 * 1024  # 256KB


class TestRunCommand:
    """Test cases for _run_command method."""

    def test_run_command_success(self, converter, mock_subprocess_run):
        """Test successful command execution."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stdout="success", stderr=""
        )
        result = converter._run_command(['echo', 'hello'])
        assert result is True
        mock_subprocess_run.assert_called_once()

    def test_run_command_failure(self, converter, mock_subprocess_run, caplog):
        """Test failed command execution."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="command failed"
        )
        with caplog.at_level(logging.ERROR):
            result = converter._run_command(['bad_command'])
            assert result is False
            assert "Command failed: bad_command" in caplog.text
            assert "Stderr: command failed" in caplog.text

    def test_run_command_not_found(self, converter, mock_subprocess_run, caplog):
        """Test command not found error."""
        mock_subprocess_run.side_effect = FileNotFoundError
        with caplog.at_level(logging.ERROR):
            result = converter._run_command(['non_existent_cmd'])
            assert result is False
            assert "Command not found: non_existent_cmd" in caplog.text

    def test_run_command_unexpected_error(self, converter, mock_subprocess_run, caplog):
        """Test an unexpected error during command execution."""
        mock_subprocess_run.side_effect = Exception("test error")
        with caplog.at_level(logging.ERROR):
            result = converter._run_command(['some_cmd'])
            assert result is False
            assert "An unexpected error occurred while running command: test error" in caplog.text


class TestGetMediaDimensions:
    """Test cases for _get_media_dimensions method."""

    def test_get_media_dimensions_success(self, converter, mock_subprocess_run, tmp_path):
        """Test successful retrieval of media dimensions."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stdout="1920x1080\n", stderr=""
        )
        dummy_file = tmp_path / "dummy.mp4"
        dummy_file.touch()

        dimensions = converter._get_media_dimensions(dummy_file)
        assert dimensions == (1920, 1080)
        mock_subprocess_run.assert_called_once()

    def test_get_media_dimensions_failure(self, converter, mock_subprocess_run, tmp_path, caplog):
        """Test failure to retrieve media dimensions."""
        mock_subprocess_run.side_effect = subprocess.SubprocessError("ffprobe error")
        dummy_file = tmp_path / "dummy.mp4"
        dummy_file.touch()

        with caplog.at_level(logging.ERROR):
            dimensions = converter._get_media_dimensions(dummy_file)
            assert dimensions is None
            assert f"Failed to get dimensions for {dummy_file.name}: ffprobe error" in caplog.text

    def test_get_media_dimensions_invalid_output(self, converter, mock_subprocess_run, tmp_path, caplog):
        """Test ffprobe returning invalid output for dimensions."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stdout="invalid_output\n", stderr=""
        )
        dummy_file = tmp_path / "dummy.mp4"
        dummy_file.touch()

        with caplog.at_level(logging.ERROR):
            dimensions = converter._get_media_dimensions(dummy_file)
            assert dimensions is None
            assert f"Failed to get dimensions for {dummy_file.name}: " in caplog.text


class TestReduceFileSize:
    """Test cases for _reduce_file_size method."""

    def test_reduce_file_size_already_small_enough(self, converter, tmp_path):
        """Test when file is already within size limit."""
        dummy_file = tmp_path / "small.webm"
        dummy_file.write_bytes(b"a" * 10000)  # 10KB
        assert dummy_file.stat().st_size < TgWebMConverter.ICON_MAX_SIZE

        result = converter._reduce_file_size(dummy_file, TgWebMConverter.ICON_MAX_SIZE, "96K", "45")
        assert result is True
        # Ensure ffmpeg command was not run
        with patch('tg_webm_converter.converter.TgWebMConverter._run_command') as mock_run_command:
            result = converter._reduce_file_size(dummy_file, TgWebMConverter.ICON_MAX_SIZE, "96K", "45")
            mock_run_command.assert_not_called()

    def test_reduce_file_size_success(self, converter, mock_subprocess_run, tmp_path):
        """Test successful re-encoding to reduce file size."""
        original_file = tmp_path / "large.webm"
        original_file.write_bytes(b"a" * 100000)  # 100KB

        temp_output = tmp_path / "large.tmp.webm"
        temp_output.write_bytes(b"b" * 20000)  # 20KB (mock reduced size)

        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0),  # for the ffmpeg re-encode
        ]

        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.side_effect = [
                MagicMock(st_size=100000),  # initial size
                MagicMock(st_size=20000),  # after re-encode and replace
            ]
            with patch.object(Path, 'unlink') as mock_unlink, \
                    patch.object(Path, 'replace') as mock_replace:
                result = converter._reduce_file_size(
                    original_file, TgWebMConverter.ICON_MAX_SIZE, "96K", "45"
                )
                assert result is True
                mock_replace.assert_called_once_with(original_file)
                mock_unlink.assert_not_called() # No unlink if replace is used and successful
                assert "libvpx-vp9" in " ".join(mock_subprocess_run.call_args[0][0])
                assert "-b:v 96K" in " ".join(mock_subprocess_run.call_args[0][0])


    def test_reduce_file_size_failure(self, converter, mock_subprocess_run, tmp_path, caplog):
        """Test re-encoding failure during size reduction."""
        original_file = tmp_path / "very_large.webm"
        original_file.write_bytes(b"a" * 100000)  # 100KB

        mock_subprocess_run.return_value = MagicMock(returncode=1)  # ffmpeg fails
        with caplog.at_level(logging.ERROR):
            with patch.object(Path, 'unlink') as mock_unlink:
                result = converter._reduce_file_size(
                    original_file, TgWebMConverter.ICON_MAX_SIZE, "96K", "45"
                )
                assert result is False
                assert "Failed during size reduction step." in caplog.text
                mock_unlink.assert_not_called() # temp file is created and then unlinked by the method

    def test_reduce_file_size_still_too_large(self, converter, mock_subprocess_run, tmp_path, caplog):
        """Test when re-encoding doesn't reduce file below max_size."""
        original_file = tmp_path / "large_but_stubborn.webm"
        original_file.write_bytes(b"a" * 100000)  # 100KB

        temp_output = tmp_path / "large_but_stubborn.tmp.webm"
        temp_output.write_bytes(b"b" * 40000)  # 40KB (still > 32KB ICON_MAX_SIZE)

        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0),  # for the ffmpeg re-encode
        ]

        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.side_effect = [
                MagicMock(st_size=100000),  # initial size
                MagicMock(st_size=40000),  # after re-encode and replace
            ]
            with patch.object(Path, 'replace') as mock_replace:
                with caplog.at_level(logging.WARNING):
                    result = converter._reduce_file_size(
                        original_file, TgWebMConverter.ICON_MAX_SIZE, "96K", "45"
                    )
                    assert result is True  # Command itself succeeded
                    mock_replace.assert_called_once_with(original_file)
                    assert "Could not reduce large_but_stubborn.webm below 32KB" in caplog.text


class TestConvertToIcon:
    """Test cases for convert_to_icon method."""

    def test_convert_to_icon_file_not_exists(self, converter, caplog):
        """Test conversion with a non-existent file."""
        nonexistent_file = "nonexistent.jpg"
        with caplog.at_level(logging.ERROR):
            result = converter.convert_to_icon(nonexistent_file)
            assert result is False
            assert len(caplog.records) == 1
            assert caplog.records[0].levelname == 'ERROR'

    @patch('tg_webm_converter.converter.TgWebMConverter._run_command')
    @patch('tg_webm_converter.converter.TgWebMConverter._reduce_file_size')
    def test_convert_to_icon_success(self, mock_reduce_file_size, mock_run_command, converter, tmp_path):
        """Test successful icon conversion."""
        input_file = tmp_path / "test.jpg"
        input_file.touch()

        mock_run_command.return_value = True
        mock_reduce_file_size.return_value = True

        result = converter.convert_to_icon(str(input_file))
        assert result is True
        mock_run_command.assert_called_once()
        mock_reduce_file_size.assert_called_once()
        assert "scale='min(100,iw)':'min(100,ih)':flags=lanczos" in " ".join(mock_run_command.call_args[0][0])
        assert "pad=100:100" in " ".join(mock_run_command.call_args[0][0])
        assert "-b:v 128K" in " ".join(mock_run_command.call_args[0][0])
        assert "-crf 35" in " ".join(mock_run_command.call_args[0][0])

    @patch('tg_webm_converter.converter.TgWebMConverter._run_command')
    @patch('tg_webm_converter.converter.TgWebMConverter._reduce_file_size')
    def test_convert_to_icon_ffmpeg_failure(self, mock_reduce_file_size, mock_run_command, converter, tmp_path):
        """Test icon conversion with ffmpeg failure."""
        input_file = tmp_path / "test.jpg"
        input_file.touch()

        mock_run_command.return_value = False
        result = converter.convert_to_icon(str(input_file))
        assert result is False
        mock_run_command.assert_called_once()
        mock_reduce_file_size.assert_not_called() # No reduction if initial conversion fails

    @patch('tg_webm_converter.converter.TgWebMConverter._run_command')
    @patch('tg_webm_converter.converter.TgWebMConverter._reduce_file_size')
    def test_convert_to_icon_reduction_failure(self, mock_reduce_file_size, mock_run_command, converter, tmp_path):
        """Test icon conversion when size reduction fails."""
        input_file = tmp_path / "test.jpg"
        input_file.touch()

        mock_run_command.return_value = True
        mock_reduce_file_size.return_value = False # Reduction fails

        result = converter.convert_to_icon(str(input_file))
        assert result is False
        mock_run_command.assert_called_once()
        mock_reduce_file_size.assert_called_once()


class TestConvertToSticker:
    """Test cases for convert_to_sticker method."""

    def test_convert_to_sticker_file_not_exists(self, converter, caplog):
        """Test sticker conversion with a non-existent file."""
        nonexistent_file = "nonexistent.jpg"
        with caplog.at_level(logging.ERROR):
            result = converter.convert_to_sticker(nonexistent_file)
            assert result is False
            assert "Failed to get dimensions for nonexistent.jpg" in caplog.text

    @patch('tg_webm_converter.converter.TgWebMConverter._get_media_dimensions')
    @patch('tg_webm_converter.converter.TgWebMConverter._run_command')
    @patch('tg_webm_converter.converter.TgWebMConverter._reduce_file_size')
    def test_convert_to_sticker_success(
        self, mock_reduce_file_size, mock_run_command, mock_get_dimensions, converter, tmp_path
    ):
        """Test successful sticker conversion."""
        input_file = tmp_path / "test.jpg"
        input_file.touch()

        mock_get_dimensions.return_value = (1000, 500)  # Landscape image
        mock_run_command.return_value = True
        mock_reduce_file_size.return_value = True

        result = converter.convert_to_sticker(str(input_file))
        assert result is True
        mock_get_dimensions.assert_called_once_with(input_file)
        mock_run_command.assert_called_once()
        mock_reduce_file_size.assert_called_once()
        # Check scale filter for landscape (512px on longest side; width)
        assert "scale=512:-1:flags=lanczos" in " ".join(mock_run_command.call_args[0][0])
        assert "-b:v 256K" in " ".join(mock_run_command.call_args[0][0])
        assert "-crf 30" in " ".join(mock_run_command.call_args[0][0])

    @patch('tg_webm_converter.converter.TgWebMConverter._get_media_dimensions')
    @patch('tg_webm_converter.converter.TgWebMConverter._run_command')
    @patch('tg_webm_converter.converter.TgWebMConverter._reduce_file_size')
    def test_convert_to_sticker_portrait_success(
        self, mock_reduce_file_size, mock_run_command, mock_get_dimensions, converter, tmp_path
    ):
        """Test successful sticker conversion for a portrait image."""
        input_file = tmp_path / "test_portrait.jpg"
        input_file.touch()

        mock_get_dimensions.return_value = (500, 1000)  # Portrait image
        mock_run_command.return_value = True
        mock_reduce_file_size.return_value = True

        result = converter.convert_to_sticker(str(input_file))
        assert result is True
        mock_get_dimensions.assert_called_once_with(input_file)
        mock_run_command.assert_called_once()
        mock_reduce_file_size.assert_called_once()
        # Check scale filter for portrait (512px on longest side; height)
        assert "scale=-1:512:flags=lanczos" in " ".join(mock_run_command.call_args[0][0])

    @patch('tg_webm_converter.converter.TgWebMConverter._get_media_dimensions')
    @patch('tg_webm_converter.converter.TgWebMConverter._run_command')
    @patch('tg_webm_converter.converter.TgWebMConverter._reduce_file_size')
    def test_convert_to_sticker_ffmpeg_failure(
        self, mock_reduce_file_size, mock_run_command, mock_get_dimensions, converter, tmp_path
    ):
        """Test sticker conversion with ffmpeg failure."""
        input_file = tmp_path / "test.jpg"
        input_file.touch()

        mock_get_dimensions.return_value = (1000, 500)
        mock_run_command.return_value = False
        result = converter.convert_to_sticker(str(input_file))
        assert result is False
        mock_get_dimensions.assert_called_once()
        mock_run_command.assert_called_once()
        mock_reduce_file_size.assert_not_called()

    @patch('tg_webm_converter.converter.TgWebMConverter._get_media_dimensions')
    def test_convert_to_sticker_get_dimensions_failure(self, mock_get_dimensions, converter, tmp_path):
        """Test sticker conversion when getting dimensions fails."""
        input_file = tmp_path / "test.jpg"
        input_file.touch()

        mock_get_dimensions.return_value = None  # Failed to get dimensions
        result = converter.convert_to_sticker(str(input_file))
        assert result is False
        mock_get_dimensions.assert_called_once()
        # Ensure _run_command and _reduce_file_size are not called
        with patch('tg_webm_converter.converter.TgWebMConverter._run_command') as mock_run_command, \
             patch('tg_webm_converter.converter.TgWebMConverter._reduce_file_size') as mock_reduce_file_size:
            converter.convert_to_sticker(str(input_file))
            mock_run_command.assert_not_called()
            mock_reduce_file_size.assert_not_called()


class TestFindSupportedFiles:
    """Test cases for find_supported_files method."""

    def test_find_supported_files_empty_directory(self, converter, tmp_path):
        """Test finding files in empty directory."""
        # tmp_path is initially empty
        files = converter.find_supported_files()
        assert files == []

    def test_find_supported_files_with_images(self, converter, tmp_path):
        """Test finding supported image files."""
        # Create a mix of supported and unsupported files
        (tmp_path / "test.jpg").touch()
        (tmp_path / "image.png").touch()
        (tmp_path / "video.mp4").touch()
        (tmp_path / "document.txt").touch()
        (tmp_path / "archive.zip").touch()
        (tmp_path / "photo.jpeg").touch()
        (tmp_path / "anim.gif").touch()
        (tmp_path / "web_icon.webp").touch()

        expected_files = sorted([
            Path("anim.gif"),
            Path("image.png"),
            Path("photo.jpeg"),
            Path("test.jpg"),
            Path("video.mp4"),
            Path("web_icon.webp"),
        ])

        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)
            files = converter.find_supported_files()
        finally:
            os.chdir(original_cwd) # Restore original CWD

        assert files == expected_files

    def test_find_supported_files_case_insensitive(self, converter, tmp_path):
        """Test finding files with different case extensions."""
        (tmp_path / "test.JPG").touch()
        (tmp_path / "image.PNG").touch()
        (tmp_path / "video.Mp4").touch()
        (tmp_path / "graphic.Bmp").touch()
        (tmp_path / "TiffFile.TIFF").touch()
        (tmp_path / "random.txt").touch()

        expected_files = sorted([]) # No files will be found with only lowercase glob patterns for uppercase extensions

        files = converter.find_supported_files()
        assert files == expected_files
