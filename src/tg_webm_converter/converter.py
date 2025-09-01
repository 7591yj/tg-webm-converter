import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class TgWebMConverter:
    """Handles conversion of media files to WebM format."""

    SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.mp4']
    ICON_MAX_SIZE = 32 * 1024  # 32KB
    STICKER_MAX_SIZE = 256 * 1024  # 256KB

    def __init__(self, output_dir: str = "./webm"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if ffmpeg and ffprobe are installed and accessible."""
        for cmd in ['ffmpeg', 'ffprobe']:
            if not shutil.which(cmd):
                logging.error("%s not found. Please install it and ensure it's in your PATH.", cmd)
                raise FileNotFoundError(f"Required command not found: {cmd}")

    def _run_command(self, args: List[str]) -> bool:
        """
        Run a subprocess command; log errors if any.

        :return: True on success (return 0), False otherwise
        """
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                logging.error(
                    "Command failed: %s\nStderr: %s",
                    " ".join(args),
                    result.stderr.strip(),
                )
                return False
            return True
        except FileNotFoundError:
            # FALLBACK; _check_dependencies() should have already checked this
            logging.error("Command not found: %s", args[0])
            return False
        except Exception as e:
            logging.error("An unexpected error occurred while running command: %s", str(e))
            return False

    def _get_media_dimensions(self, input_path: Path) -> Optional[Tuple[int, int]]:
        """Get the width and height of a media file, using ffprobe"""
        args = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0:s=x",
            str(input_path),
        ]
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, check=True
            )
            width, height = map(int, result.stdout.strip().split('x'))
            return width, height
        except (subprocess.SubprocessError, ValueError) as e:
            logging.error("Failed to get dimensions for %s: %s", input_path.name, e)
            return None

    def _reduce_file_size(self, file_path: Path, max_size: int, bitrate: str, crf: str) -> bool:
        """Re-encodes the WebM file to reduce the size"""
        if file_path.stat().st_size <= max_size:
            return True  # Already within size limit

        logging.info("File is too large, attempting to reduce size for %s...", file_path.name)
        temp_output = file_path.with_suffix('.tmp.webm')

        args = [
            "ffmpeg", "-y", "-i", str(file_path),
            "-c:v", "libvpx-vp9",
            "-b:v", bitrate,
            "-crf", crf,
            "-pix_fmt", "yuva420p",
            str(temp_output),
        ]

        if not self._run_command(args):
            logging.error("Failed during size reduction step.")
            if temp_output.exists():
                temp_output.unlink()
            return False

        temp_output.replace(file_path)
        final_size = file_path.stat().st_size
        if final_size > max_size:
            logging.warning(
                "Could not reduce %s below %dKB. Final size: %dKB",
                file_path.name, max_size // 1024, final_size // 1024,
            )
        return True

    def convert_to_icon(self, input_file: str) -> bool:
        """Convert media to a 100x100 icon WebM."""
        input_path = Path(input_file)
        output_path = self.output_dir / f"{input_path.stem}_icon.webm"

        # 100x100 square with a transparent background
        filter_str = (
            "scale='min(100,iw)':'min(100,ih)':flags=lanczos,"
            "pad=100:100:(ow-iw)/2:(oh-ih)/2:color=0x00000000"
        )

        args = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-vf", f"{filter_str},fps=30",
            "-t", "3", "-an",
            "-c:v", "libvpx-vp9",
            "-b:v", "128K", "-crf", "35",
            "-pix_fmt", "yuva420p",
            str(output_path),
        ]

        if not self._run_command(args):
            return False

        return self._reduce_file_size(
            output_path, self.ICON_MAX_SIZE, bitrate="96K", crf="45"
        )

    def convert_to_sticker(self, input_file: str) -> bool:
        """Convert media to a 512px sticker WebM."""
        input_path = Path(input_file)
        output_path = self.output_dir / f"{input_path.stem}.webm"

        dimensions = self._get_media_dimensions(input_path)
        if not dimensions:
            return False
        width, height = dimensions

        # Scale to 512px on the longest side
        scale_filter = "scale=512:-1:flags=lanczos"
        if height > width:
            scale_filter = "scale=-1:512:flags=lanczos"

        args = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-vf", f"{scale_filter},fps=30",
            "-t", "3", "-an",
            "-c:v", "libvpx-vp9",
            "-b:v", "256K", "-crf", "30",
            "-pix_fmt", "yuva420p",
            str(output_path),
        ]

        if not self._run_command(args):
            return False

        return self._reduce_file_size(
            output_path, self.STICKER_MAX_SIZE, bitrate="200K", crf="35"
        )

    def find_supported_files(self) -> List[Path]:
        """Find all supported media files in the current directory."""
        files = [
            p
            for ext in self.SUPPORTED_EXTENSIONS
            for p in Path(".").glob(f"*{ext}")
        ]
        # Remove duplicates from case-insensitivity (e.g. .png, .PNG)
        return sorted(list(set(files)))
