import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

from tg_webm_converter.cli import main, parse_arguments


def run_main_with_args(args):
    with patch.object(sys, 'argv',["prog_name"] + args):
        main()

class TestCLI:
    """Test cases for CLI functionality."""

    @patch('tg_webm_converter.cli.ConversionRunner')
    def test_main_no_arguments_no_files(self, mock_runner_class, caplog):
        """Test main with no arguments and no image files."""
        mock_instance = mock_runner_class.return_value
        mock_instance.run.return_value = True # Simulate success

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        mock_runner_class.assert_called_once()
        mock_instance.run.assert_called_once()

    @patch("tg_webm_converter.cli.ConversionRunner")
    def test_main_icon_file_argument(self, mock_runner_class):
        """Test main correctly parses --icon-file and passes it to the runner."""
        mock_instance = mock_runner_class.return_value
        mock_instance.run.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            run_main_with_args(["--icon-file", "icon.png"])

        assert exc_info.value.code == 0
        # Assert the runner was initialized with the correct parsed arguments
        called_args = mock_runner_class.call_args[0][0]
        assert called_args.icon_file == "icon.png"
        assert called_args.file is None

    @patch("tg_webm_converter.cli.ConversionRunner")
    def test_main_single_file_argument(self, mock_runner_class):
        """Test main correctly parses --file and passes it to the runner."""
        mock_instance = mock_runner_class.return_value
        mock_instance.run.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            run_main_with_args(["--file", "sticker.jpg"])

        assert exc_info.value.code == 0
        called_args = mock_runner_class.call_args[0][0]
        assert called_args.file == "sticker.jpg"

    @patch("tg_webm_converter.cli.ConversionRunner")
    def test_main_custom_output_directory(self, mock_runner_class):
        """Test main correctly parses -o and passes it to the runner."""
        mock_instance = mock_runner_class.return_value
        mock_instance.run.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            run_main_with_args(["-o", "./custom_output"])

        assert exc_info.value.code == 0
        called_args = mock_runner_class.call_args[0][0]
        assert called_args.output == "./custom_output"

    @patch("tg_webm_converter.cli.ConversionRunner")
    def test_main_runner_fails(self, mock_runner_class):
        """Test that main exits with 1 if the runner returns False."""
        mock_instance = mock_runner_class.return_value
        mock_instance.run.return_value = False  # Simulate a conversion failure

        with pytest.raises(SystemExit) as exc_info:
            run_main_with_args([])

        assert exc_info.value.code == 1

    @patch("tg_webm_converter.cli.ConversionRunner")
    def test_main_keyboard_interrupt(self, mock_runner_class, caplog):
        """Test main handling keyboard interrupt from the runner."""
        mock_instance = mock_runner_class.return_value
        mock_instance.run.side_effect = KeyboardInterrupt()

        caplog.set_level(logging.INFO)

        with pytest.raises(SystemExit) as exc_info:
            run_main_with_args([])

        assert exc_info.value.code == 1
        assert len(caplog.records) > 0
        assert caplog.records[-1].message == "\nOperation cancelled by user."

    @patch("tg_webm_converter.cli.ConversionRunner")
    def test_main_unexpected_exception(self, mock_runner_class, caplog):
        """Test main handling unexpected exception from the runner."""
        mock_instance = mock_runner_class.return_value
        mock_instance.run.side_effect = Exception("A wild error appears!")

        caplog.set_level(logging.ERROR)

        with pytest.raises(SystemExit) as exc_info:
            run_main_with_args([])

        assert exc_info.value.code == 1
        assert any(
            r.levelname == 'ERROR' and "An error occurred: A wild error appears!" in r.message
            for r in caplog.records
        )
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == 'ERROR'
        assert caplog.records[0].message == "An error occurred: %s" % "A wild error appears!"

class TestArgumentParsing:
    """
    Test argument parsing directly. These tests don't need mocks as they
    test argparse itself, which is handled before the runner is called.
    """

    def test_help_output(self, capsys):
        """Test help message output."""
        with pytest.raises(SystemExit) as exc_info:
            run_main_with_args(["--help"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Convert images to Telegram WebM stickers" in captured.out

    def test_mutually_exclusive_arguments(self, capsys):
        """Test that mutually exclusive arguments raise an error."""
        with pytest.raises(SystemExit) as exc_info:
            run_main_with_args(["--icon", "test.jpg", "--file", "other.png"])

        # argparse exits with code 2 for usage errors
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "not allowed with argument" in captured.err