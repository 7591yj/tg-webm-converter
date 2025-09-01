import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from tg_webm_converter.runner import ConversionRunner

# A fixture to create a basic args namespace for tests
@pytest.fixture
def mock_args():
    return argparse.Namespace(
        icon=None,
        file=None,
        icon_file=None,
        output="./webm_test",
    )


@patch("tg_webm_converter.runner.TgWebMConverter")
def test_runner_single_file(mock_converter_class, mock_args):
    """Test that runner calls convert_to_sticker for a single file."""
    mock_args.file = "sticker.png"
    mock_converter_instance = mock_converter_class.return_value
    mock_converter_instance.convert_to_sticker.return_value = True

    with patch("pathlib.Path.exists", return_value=True):
        runner = ConversionRunner(mock_args)
        assert runner.run() is True

    mock_converter_class.assert_called_once_with("./webm_test")
    mock_converter_instance.convert_to_sticker.assert_called_once_with("sticker.png")


@patch("tg_webm_converter.runner.TgWebMConverter")
def test_runner_single_icon(mock_converter_class, mock_args):
    """Test that runner calls convert_to_icon for a single icon file."""
    mock_args.icon_file = "icon.png"
    mock_converter_instance = mock_converter_class.return_value
    mock_converter_instance.convert_to_icon.return_value = True

    with patch("pathlib.Path.exists", return_value=True):
        runner = ConversionRunner(mock_args)
        assert runner.run() is True

    mock_converter_instance.convert_to_icon.assert_called_once_with("icon.png")


@patch("tg_webm_converter.runner.TgWebMConverter")
def test_runner_batch_mode(mock_converter_class, mock_args):
    """Test the batch conversion workflow."""
    mock_args.icon = "icon.png"
    mock_converter_instance = mock_converter_class.return_value
    mock_converter_instance.find_supported_files.return_value = [
        Path("icon.png"),
        Path("sticker1.jpg"),
        Path("sticker2.gif"),
    ]
    # Simulate all conversions succeeding
    mock_converter_instance.convert_to_icon.return_value = True
    mock_converter_instance.convert_to_sticker.return_value = True

    with patch("pathlib.Path.exists", return_value=True):
        runner = ConversionRunner(mock_args)
        assert runner.run() is True

    # Check calls
    mock_converter_instance.convert_to_icon.assert_called_once_with("icon.png")
    assert mock_converter_instance.convert_to_sticker.call_count == 2
    mock_converter_instance.convert_to_sticker.assert_any_call("sticker1.jpg")
    mock_converter_instance.convert_to_sticker.assert_any_call("sticker2.gif")


@patch("tg_webm_converter.runner.TgWebMConverter")
def test_runner_validation_fails(mock_converter_class, mock_args):
    """Test that the runner stops if a file does not exist."""
    mock_args.file = "nonexistent.png"

    with patch("pathlib.Path.exists", return_value=False):
        runner = ConversionRunner(mock_args)
        assert runner.run() is False

    # Ensure no conversion methods were ever called
    mock_converter_instance = mock_converter_class.return_value
    mock_converter_instance.convert_to_sticker.assert_not_called()