import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tg_webm_converter.converter import TgWebMConverter


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_images(temp_dir):
    """Create sample image files for testing."""
    images = {}

    # Create dummy image files
    image_files = [
        "test.jpg",
        "test.png",
        "test.gif",
        "icon.webp",
        "large_image.jpeg"
    ]

    for filename in image_files:
        file_path = temp_dir / filename
        file_path.write_bytes(b"fake_image_data")
        images[filename] = file_path

    return images


@pytest.fixture
def converter(temp_dir):
    """Create a TgWebMConverter instance with temp output directory."""
    output_dir = temp_dir / "webm"
    return TgWebMConverter(str(output_dir))


@pytest.fixture
def mock_ffmpeg_success():
    """Mock successful ffmpeg execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        yield mock_run


@pytest.fixture
def mock_ffmpeg_failure():
    """Mock failed ffmpeg execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        yield mock_run


@pytest.fixture
def mock_ffprobe_success():
    """Mock successful ffprobe execution for getting dimensions."""
    with patch('subprocess.run') as mock_run:
        # Mock ffprobe calls for width and height
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="1024"),  # width
            MagicMock(returncode=0, stdout="768")  # height
        ]
        yield mock_run
