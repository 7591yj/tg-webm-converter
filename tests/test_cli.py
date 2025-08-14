import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from tg_webm_converter.cli import main


class TestCLI:
    """Test cases for CLI functionality."""

    def test_main_no_arguments_no_files(self, capsys, monkeypatch):
        """Test main with no arguments and no image files."""
        monkeypatch.setattr(sys, 'argv', ['tg-webm-converter'])

        with patch('tg_webm_converter.cli.TgWebMConverter') as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.find_supported_files.return_value = []

            # This DOES raise SystemExit(0) when no files found
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            assert "No supported image files found" in captured.out

    def test_main_convert_all_files_success(self, capsys, monkeypatch):
        """Test main converting all files successfully."""
        monkeypatch.setattr(sys, 'argv', ['tg-webm-converter'])

        mock_files = [Path("test1.jpg"), Path("test2.png")]

        with patch('tg_webm_converter.cli.TgWebMConverter') as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.find_supported_files.return_value = mock_files
            mock_instance.convert_to_sticker.return_value = True
            mock_instance.output_dir = Path("./webm")

            # This should NOT raise SystemExit for successful completion
            main()

            captured = capsys.readouterr()
            assert "Conversion complete! 2/2 files converted" in captured.out

    def test_main_icon_file_argument(self, monkeypatch, temp_dir):
        """Test main with --icon-file argument."""
        test_file = temp_dir / "icon.png"
        test_file.write_bytes(b"fake_image")

        monkeypatch.setattr(sys, 'argv',
                            ['tg-webm-converter', '--icon-file', str(test_file)])

        with patch('tg_webm_converter.cli.TgWebMConverter') as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.convert_to_icon.return_value = True

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_instance.convert_to_icon.assert_called_once_with(str(test_file))

    def test_main_single_file_argument(self, monkeypatch, temp_dir):
        """Test main with --file argument."""
        test_file = temp_dir / "sticker.jpg"
        test_file.write_bytes(b"fake_image")

        monkeypatch.setattr(sys, 'argv',
                            ['tg-webm-converter', '--file', str(test_file)])

        with patch('tg_webm_converter.cli.TgWebMConverter') as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.convert_to_sticker.return_value = True

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_instance.convert_to_sticker.assert_called_once_with(str(test_file))

    def test_main_icon_with_others(self, monkeypatch, temp_dir):
        """Test main with --icon argument (convert one to icon, others to stickers)."""
        icon_file = temp_dir / "icon.png"
        icon_file.write_bytes(b"fake_image")

        monkeypatch.setattr(sys, 'argv',
                            ['tg-webm-converter', '--icon', str(icon_file)])

        mock_files = [Path(str(icon_file)), Path("other.jpg")]

        with patch('tg_webm_converter.cli.TgWebMConverter') as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.find_supported_files.return_value = mock_files
            mock_instance.convert_to_icon.return_value = True
            mock_instance.convert_to_sticker.return_value = True
            mock_instance.output_dir = Path("./webm")

            # This should NOT raise SystemExit for successful completion
            main()

            mock_instance.convert_to_icon.assert_called_once_with(str(icon_file))
            mock_instance.convert_to_sticker.assert_called_once_with("other.jpg")

    def test_main_file_not_exists(self, capsys, monkeypatch):
        """Test main with non-existent file."""
        monkeypatch.setattr(sys, 'argv',
                            ['tg-webm-converter', '--file', 'nonexistent.jpg'])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not exist" in captured.out

    def test_main_custom_output_directory(self, monkeypatch, temp_dir):
        """Test main with custom output directory."""
        output_dir = temp_dir / "custom_output"

        monkeypatch.setattr(sys, 'argv',
                            ['tg-webm-converter', '-o', str(output_dir)])

        with patch('tg_webm_converter.cli.TgWebMConverter') as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.find_supported_files.return_value = []

            # This DOES raise SystemExit(0) when no files found
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_converter.assert_called_once_with(str(output_dir))

    def test_main_keyboard_interrupt(self, capsys, monkeypatch):
        """Test main handling keyboard interrupt."""
        monkeypatch.setattr(sys, 'argv', ['tg-webm-converter'])

        with patch('tg_webm_converter.cli.TgWebMConverter') as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.find_supported_files.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "interrupted by user" in captured.out

    def test_main_unexpected_exception(self, capsys, monkeypatch):
        """Test main handling unexpected exception."""
        monkeypatch.setattr(sys, 'argv', ['tg-webm-converter'])

        with patch('tg_webm_converter.cli.TgWebMConverter') as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.find_supported_files.side_effect = Exception("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Unexpected error" in captured.out

    def test_main_partial_success(self, capsys, monkeypatch):
        """Test main with some files failing conversion."""
        monkeypatch.setattr(sys, 'argv', ['tg-webm-converter'])

        mock_files = [Path("success.jpg"), Path("fail.png")]

        with patch('tg_webm_converter.cli.TgWebMConverter') as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.find_supported_files.return_value = mock_files
            # First call succeeds, second fails
            mock_instance.convert_to_sticker.side_effect = [True, False]
            mock_instance.output_dir = Path("./webm")

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1  # Exit with error due to failures
            captured = capsys.readouterr()
            assert "1/2 files converted" in captured.out


class TestArgumentParsing:
    """Test argument parsing edge cases."""

    def test_help_output(self, capsys, monkeypatch):
        """Test help message output."""
        monkeypatch.setattr(sys, 'argv', ['tg-webm-converter', '--help'])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Convert images to Telegram WebM stickers" in captured.out

    def test_mutually_exclusive_arguments(self, capsys, monkeypatch):
        """Test that mutually exclusive arguments raise error."""
        monkeypatch.setattr(sys, 'argv',
                            ['tg-webm-converter', '--icon', 'test.jpg',
                             '--file', 'other.png'])

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2  # Argument parsing error