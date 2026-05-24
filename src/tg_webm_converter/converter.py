import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class ConversionTask:
    """Represents a single conversion request."""

    asset_id: str
    source_path: str
    mode: str


@dataclass(frozen=True)
class ConversionResult:
    """Represents the result of a single conversion operation."""

    asset_id: Optional[str]
    source_path: str
    mode: str
    success: bool
    output_path: Optional[str] = None
    size_bytes: Optional[int] = None
    error: Optional[str] = None


class TgWebMConverter:
    """Handles conversion of media files to WebM format."""

    SUPPORTED_EXTENSIONS = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".tiff",
        ".mp4",
        ".webm",
    ]
    ICON_MAX_SIZE = 32 * 1024
    STICKER_MAX_SIZE = 256 * 1024

    def __init__(
        self,
        output_dir: str = "./webm",
        ffmpeg_command: str = "ffmpeg",
        ffprobe_command: str = "ffprobe",
    ):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.ffmpeg_command = ffmpeg_command
        self.ffprobe_command = ffprobe_command
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if ffmpeg is installed and accessible."""
        if not shutil.which(self.ffmpeg_command):
            logging.error(
                "%s not found. Please install it and ensure it's in your PATH.",
                self.ffmpeg_command,
            )
            raise FileNotFoundError(
                f"Required command not found: {self.ffmpeg_command}"
            )

    def _run_command(self, args: Sequence[str]) -> bool:
        """Run a subprocess command; log errors if any."""
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
            logging.error("Command not found: %s", args[0])
            return False
        except Exception as error:
            logging.error(
                "An unexpected error occurred while running command: %s",
                str(error),
            )
            return False

    def is_supported_file(self, input_path: Path) -> bool:
        return input_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def _reduce_file_size(
        self, file_path: Path, max_size: int, bitrate: str, crf: str
    ) -> bool:
        if file_path.stat().st_size <= max_size:
            return True

        logging.info(
            "File is too large, attempting to reduce size for %s...",
            file_path.name,
        )
        temp_output = file_path.with_suffix(".tmp.webm")

        args = [
            self.ffmpeg_command,
            "-y",
            "-i",
            str(file_path),
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            bitrate,
            "-crf",
            crf,
            "-pix_fmt",
            "yuva420p",
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
                file_path.name,
                max_size // 1024,
                final_size // 1024,
            )
        return True

    def _build_output_path(
        self,
        input_path: Path,
        mode: str,
        output_filename: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Path:
        if output_path:
            return Path(output_path).resolve()

        if output_filename:
            return self.output_dir / output_filename

        if mode == "icon":
            return self.output_dir / f"{input_path.stem}_icon.webm"

        return self.output_dir / f"{input_path.stem}.webm"

    def _validate_input(
        self, input_path: Path, mode: str
    ) -> Optional[ConversionResult]:
        if not input_path.exists():
            logging.error("Input file not found: %s", input_path)
            return ConversionResult(
                asset_id=None,
                source_path=str(input_path),
                mode=mode,
                success=False,
                error=f"Input file not found: {input_path}",
            )

        if not self.is_supported_file(input_path):
            error = f"Unsupported input file: {input_path}"
            logging.error(error)
            return ConversionResult(
                asset_id=None,
                source_path=str(input_path),
                mode=mode,
                success=False,
                error=error,
            )

        return None

    def convert_file(
        self,
        input_file: str,
        mode: str,
        output_filename: Optional[str] = None,
        output_path: Optional[str] = None,
        asset_id: Optional[str] = None,
    ) -> ConversionResult:
        input_path = Path(input_file).resolve()
        validation_error = self._validate_input(input_path, mode)
        if validation_error:
            return ConversionResult(
                asset_id=asset_id,
                source_path=validation_error.source_path,
                mode=mode,
                success=False,
                error=validation_error.error,
            )

        resolved_output_path = self._build_output_path(
            input_path, mode, output_filename, output_path
        )
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

        if mode == "icon":
            return self._convert_to_icon_result(
                input_path, resolved_output_path, asset_id
            )
        if mode == "sticker":
            return self._convert_to_sticker_result(
                input_path, resolved_output_path, asset_id
            )

        return ConversionResult(
            asset_id=asset_id,
            source_path=str(input_path),
            mode=mode,
            success=False,
            error=f"Unsupported conversion mode: {mode}",
        )

    def _convert_to_icon_result(
        self, input_path: Path, output_path: Path, asset_id: Optional[str]
    ) -> ConversionResult:
        filter_str = (
            "scale='min(100,iw)':'min(100,ih)':flags=lanczos,"
            "pad=100:100:(ow-iw)/2:(oh-ih)/2:color=0x00000000"
        )

        args = [
            self.ffmpeg_command,
            "-y",
            "-i",
            str(input_path),
            "-vf",
            f"{filter_str},fps=30",
            "-t",
            "3",
            "-an",
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            "128K",
            "-crf",
            "35",
            "-pix_fmt",
            "yuva420p",
            str(output_path),
        ]

        if not self._run_command(args):
            return ConversionResult(
                asset_id=asset_id,
                source_path=str(input_path),
                mode="icon",
                success=False,
                error="ffmpeg failed during icon conversion",
            )

        if not self._reduce_file_size(
            output_path, self.ICON_MAX_SIZE, bitrate="96K", crf="45"
        ):
            return ConversionResult(
                asset_id=asset_id,
                source_path=str(input_path),
                mode="icon",
                success=False,
                error="Failed to reduce icon file size",
            )

        return ConversionResult(
            asset_id=asset_id,
            source_path=str(input_path),
            mode="icon",
            success=True,
            output_path=str(output_path),
            size_bytes=output_path.stat().st_size,
        )

    def _convert_to_sticker_result(
        self, input_path: Path, output_path: Path, asset_id: Optional[str]
    ) -> ConversionResult:
        scale_filter = (
            "scale='if(gte(iw,ih),512,-1)':'if(gte(iw,ih),-1,512)'"
            ":flags=lanczos"
        )

        args = [
            self.ffmpeg_command,
            "-y",
            "-i",
            str(input_path),
            "-vf",
            f"{scale_filter},fps=30",
            "-t",
            "3",
            "-an",
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            "256K",
            "-crf",
            "30",
            "-pix_fmt",
            "yuva420p",
            str(output_path),
        ]

        if not self._run_command(args):
            return ConversionResult(
                asset_id=asset_id,
                source_path=str(input_path),
                mode="sticker",
                success=False,
                error="ffmpeg failed during sticker conversion",
            )

        if not self._reduce_file_size(
            output_path, self.STICKER_MAX_SIZE, bitrate="200K", crf="35"
        ):
            return ConversionResult(
                asset_id=asset_id,
                source_path=str(input_path),
                mode="sticker",
                success=False,
                error="Failed to reduce sticker file size",
            )

        return ConversionResult(
            asset_id=asset_id,
            source_path=str(input_path),
            mode="sticker",
            success=True,
            output_path=str(output_path),
            size_bytes=output_path.stat().st_size,
        )

    def convert_to_icon(self, input_file: str) -> bool:
        return self.convert_file(input_file, "icon").success

    def convert_to_sticker(self, input_file: str) -> bool:
        return self.convert_file(input_file, "sticker").success

    def convert_tasks(
        self,
        tasks: Iterable[ConversionTask],
        output_name_overrides: Optional[dict] = None,
    ) -> List[ConversionResult]:
        overrides = output_name_overrides or {}
        results: List[ConversionResult] = []

        for task in tasks:
            results.append(
                self.convert_file(
                    task.source_path,
                    task.mode,
                    output_filename=overrides.get(task.asset_id),
                    asset_id=task.asset_id,
                )
            )

        return results

    def find_supported_files(self, search_dir: str = ".") -> List[Path]:
        root = Path(search_dir)
        files = [
            path
            for path in root.iterdir()
            if path.is_file() and self.is_supported_file(path)
        ]
        return sorted(files)
