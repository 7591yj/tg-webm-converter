from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from tg_webm_converter.converter import TgWebMConverter


class TestTgWebMConverter:
    """Test cases for TgWebMConverter class."""

    def test_init_creates_output_directory(self, temp_dir):
        """Test that initialization creates output directory."""
        output_dir = temp_dir / "test_output"
        converter = TgWebMConverter(str(output_dir))

        assert output_dir.exists()
        assert converter.output_dir == output_dir

    def test_init_with_existing_directory(self, temp_dir):
        """Test initialization with existing output directory."""
        output_dir = temp_dir / "existing"
        output_dir.mkdir()

        converter = TgWebMConverter(str(output_dir))
        assert converter.output_dir == output_dir

    def test_supported_extensions(self):
        """Test that supported extensions are correctly defined."""
        expected_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'
        ]
        assert TgWebMConverter.SUPPORTED_EXTENSIONS == expected_extensions

    def test_size_limits(self):
        """Test that size limits are correctly defined."""
        assert TgWebMConverter.ICON_MAX_SIZE == 32 * 1024  # 32KB
        assert TgWebMConverter.STICKER_MAX_SIZE == 256 * 1024  # 256KB


class TestRunFFmpeg:
    """Test cases for _run_ffmpeg method."""

    def test_run_ffmpeg_success(self, converter, mock_ffmpeg_success):
        """Test successful ffmpeg execution."""
        with patch('tempfile.NamedTemporaryFile') as mock_temp, \
                patch('os.unlink') as mock_unlink:
            mock_temp.return_value.__enter__.return_value.name = "test.log"

            result = converter._run_ffmpeg(['-version'])

            assert result is True
            mock_ffmpeg_success.assert_called_once()
            mock_unlink.assert_called_once_with("test.log")

    def test_run_ffmpeg_failure(self, converter, mock_ffmpeg_failure, capsys):
        """Test failed ffmpeg execution."""
        with patch('tempfile.NamedTemporaryFile') as mock_temp, \
                patch('os.unlink') as mock_unlink:
            mock_file = MagicMock()
            mock_file.name = "test.log"
            mock_file.read.return_value = "ffmpeg error message"
            mock_temp.return_value.__enter__.return_value = mock_file

            result = converter._run_ffmpeg(['-invalid'])

            assert result is False
            captured = capsys.readouterr()
            assert "FFmpeg error" in captured.out

    def test_run_ffmpeg_not_found(self, converter, capsys):
        """Test ffmpeg not found error."""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            result = converter._run_ffmpeg(['-version'])

            assert result is False
            captured = capsys.readouterr()
            assert "ffmpeg not found" in captured.out


class TestConvertToIcon:
    """Test cases for convert_to_icon method."""

    def test_convert_to_icon_file_not_exists(self, converter, capsys):
        """Test conversion with a non-existent file."""
        result = converter.convert_to_icon("nonexistent.jpg")

        assert result is False
        captured = capsys.readouterr()
        assert "does not exist" in captured.out

    @patch('tg_webm_converter.converter.TgWebMConverter._run_ffmpeg')
    def test_convert_to_icon_success(self, mock_run_ffmpeg, converter,
                                     sample_images, capsys):
        """Test successful icon conversion."""
        mock_run_ffmpeg.return_value = True

        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 30 * 1024  # 30KB

            result = converter.convert_to_icon(str(sample_images["test.jpg"]))

            assert result is True
            assert mock_run_ffmpeg.call_count >= 1
            captured = capsys.readouterr()
            assert "✅ Done" in captured.out

    def test_icon_size_limit_constant(self):
        """Test that icon size limit is properly defined."""
        assert TgWebMConverter.ICON_MAX_SIZE == 32 * 1024

    @patch('tg_webm_converter.converter.TgWebMConverter._run_ffmpeg')
    def test_convert_to_icon_ffmpeg_failure(self, mock_run_ffmpeg, converter,
                                            sample_images, capsys):
        """Test icon conversion with ffmpeg failure."""
        mock_run_ffmpeg.return_value = False

        result = converter.convert_to_icon(str(sample_images["test.jpg"]))

        assert result is False
        captured = capsys.readouterr()
        assert "❌ Failed" in captured.out


class TestConvertToSticker:
    """Test cases for convert_to_sticker method."""

    def test_convert_to_sticker_file_not_exists(self, converter, capsys):
        """Test sticker conversion with a non-existent file."""
        result = converter.convert_to_sticker("nonexistent.jpg")

        assert result is False
        captured = capsys.readouterr()
        assert "does not exist" in captured.out

    @patch('subprocess.run')
    @patch('tg_webm_converter.converter.TgWebMConverter._run_ffmpeg')
    def test_convert_to_sticker_success(self, mock_run_ffmpeg, mock_subprocess,
                                        converter, sample_images, capsys):
        """Test successful sticker conversion."""
        mock_run_ffmpeg.return_value = True

        # Mock ffprobe calls for dimensions
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout="1024"),  # width
            MagicMock(returncode=0, stdout="768")  # height
        ]

        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 200 * 1024  # 200KB

            result = converter.convert_to_sticker(str(sample_images["test.jpg"]))

            assert result is True
            captured = capsys.readouterr()
            assert "✅ Done" in captured.out

    def test_sticker_size_limit_constant(self):
        """Test that sticker size limit is properly defined."""
        assert TgWebMConverter.STICKER_MAX_SIZE == 256 * 1024

    @patch('tg_webm_converter.converter.TgWebMConverter._run_ffmpeg')
    def test_convert_to_sticker_ffmpeg_failure(self, mock_run_ffmpeg, converter,
                                               sample_images, capsys):
        """Test icon conversion with ffmpeg failure."""
        mock_run_ffmpeg.return_value = False

        result = converter.convert_to_sticker(str(sample_images["test.jpg"]))

        assert result is False
        captured = capsys.readouterr()
        assert "❌ Failed" in captured.out


class TestFindSupportedFiles:
    """Test cases for find_supported_files method."""

    def test_find_supported_files_empty_directory(self, converter):
        """Test finding files in empty directory."""
        with patch.object(Path, 'glob', return_value=[]):
            files = converter.find_supported_files()
            assert files == []

    def test_find_supported_files_with_images(self, converter):
        """Test finding supported image files."""
        mock_files = [
            Path("test.jpg"),
            Path("image.png"),
            Path("icon.gif")
        ]

        with patch.object(Path, 'glob') as mock_glob:
            # Mock glob to return different files for different extensions
            mock_glob.side_effect = lambda pattern: (
                [Path("test.jpg")] if "*.jpg" in pattern else
                [Path("image.png")] if "*.png" in pattern else
                [Path("icon.gif")] if "*.gif" in pattern else
                []
            )

            files = converter.find_supported_files()

            # Should call glob for each supported extension (both cases)
            assert mock_glob.call_count == len(TgWebMConverter.SUPPORTED_EXTENSIONS) * 2

    def test_find_supported_files_case_insensitive(self, converter):
        """Test finding files with different case extensions."""
        with patch.object(Path, 'glob') as mock_glob:
            mock_glob.side_effect = lambda pattern: (
                [Path("test.JPG")] if "*.JPG" in pattern else
                [Path("image.png")] if "*.png" in pattern else
                []
            )

            files = converter.find_supported_files()

            # Verify both lowercase and uppercase patterns are searched
            call_patterns = [call[0][0] for call in mock_glob.call_args_list]
            assert any("*.jpg" in pattern for pattern in call_patterns)
            assert any("*.JPG" in pattern for pattern in call_patterns)
