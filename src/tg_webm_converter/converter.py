import os
import subprocess
import tempfile
from pathlib import Path
from typing import List


class TgWebMConverter:
    """Handles conversion of images to WebM format for stickers and icons."""

    SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff']
    ICON_MAX_SIZE = 32 * 1024  # 32KB
    STICKER_MAX_SIZE = 256 * 1024  # 256KB

    def __init__(self, output_dir: str = "./webm"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def _run_ffmpeg(self, args: List[str]) -> bool:
        """Run ffmpeg command and return success status."""
        try:
            with tempfile.NamedTemporaryFile(mode='w+', delete=False) as logfile:
                result = subprocess.run(
                    ['ffmpeg'] + args,
                    stdout=subprocess.DEVNULL,
                    stderr=logfile,
                    text=True
                )

                if result.returncode != 0:
                    logfile.seek(0)
                    print(f"❌ FFmpeg error: {logfile.read()}")
                    return False

                return True
        except FileNotFoundError:
            print("❌ Error: ffmpeg not found. Please install ffmpeg.")
            return False
        finally:
            if 'logfile' in locals():
                os.unlink(logfile.name)

    def convert_to_icon(self, input_file: str) -> bool:
        """Convert image to 100x100 icon WebM (max 32KB)."""
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"❌ Error: File '{input_file}' does not exist")
            return False

        output_path = self.output_dir / f"{input_path.stem}_icon.webm"
        print(f"Converting to icon: {input_path.name:<30} ", end="", flush=True)

        # Icon filter: pad to 100x100 square with transparent background
        filter_str = (
            "scale='if(gt(iw,ih),100,-1)':'if(gt(ih,iw),100,-1)',"
            "scale='min(iw,100)':'min(ih,100)',"
            "pad=100:100:(ow-iw)/2:(oh-ih)/2:color=0x00000000"
        )

        # Initial conversion
        args = [
            '-y', '-loglevel', 'error',
            '-i', str(input_path),
            '-vf', f"{filter_str},fps=30",
            '-t', '3',
            '-an',
            '-c:v', 'libvpx-vp9',
            '-b:v', '150K',
            '-crf', '25',
            '-pix_fmt', 'yuva420p',
            str(output_path)
        ]

        if not self._run_ffmpeg(args):
            print("❌ Failed")
            return False

        # Check and reduce file size if needed
        file_size = output_path.stat().st_size
        bitrate = 150
        crf = 25

        while file_size > self.ICON_MAX_SIZE and bitrate > 50:
            bitrate -= 20
            crf += 3
            if crf > 45:
                crf = 45

            temp_output = output_path.with_suffix('.tmp.webm')
            args = [
                '-y', '-loglevel', 'error',
                '-i', str(input_path),
                '-vf', f"{filter_str},fps=30",
                '-t', '3',
                '-an',
                '-c:v', 'libvpx-vp9',
                '-b:v', f'{bitrate}K',
                '-crf', str(crf),
                '-pix_fmt', 'yuva420p',
                str(temp_output)
            ]

            if not self._run_ffmpeg(args):
                print("❌ Failed during size reduction")
                return False

            temp_output.replace(output_path)
            file_size = output_path.stat().st_size

        if file_size > self.ICON_MAX_SIZE:
            print(f"⚠️  Warning: Could not reduce below 32KB (current: {file_size // 1024}KB)")
        else:
            print(f"✅ Done ({file_size // 1024}KB)")

        return True

    def convert_to_sticker(self, input_file: str) -> bool:
        """Convert image to 512x512 sticker WebM."""
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"❌ Error: File '{input_file}' does not exist")
            return False

        output_path = self.output_dir / f"{input_path.stem}.webm"
        print(f"Converting to sticker: {input_path.name:<30} ", end="", flush=True)

        # Get original dimensions using ffprobe
        try:
            width_result = subprocess.run([
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=width', '-of', 'csv=p=0',
                str(input_path)
            ], capture_output=True, text=True)

            height_result = subprocess.run([
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=height', '-of', 'csv=p=0',
                str(input_path)
            ], capture_output=True, text=True)

            width = int(width_result.stdout.strip())
            height = int(height_result.stdout.strip())

        except (subprocess.SubprocessError, ValueError):
            print("❌ Failed to get image dimensions")
            return False

        # Determine scale filter
        if width >= height:
            filter_str = "scale=512:-1:flags=lanczos"
        else:
            filter_str = "scale=-1:512:flags=lanczos"

        args = [
            '-y', '-loglevel', 'error',
            '-i', str(input_path),
            '-vf', f"{filter_str},fps=30",
            '-t', '3',
            '-an',
            '-c:v', 'libvpx-vp9',
            '-b:v', '256K',
            '-crf', '30',
            '-pix_fmt', 'yuva420p',
            str(output_path)
        ]

        if not self._run_ffmpeg(args):
            print("❌ Failed")
            return False

        # Check file size and reduce if needed
        file_size = output_path.stat().st_size
        if file_size > self.STICKER_MAX_SIZE:
            temp_output = output_path.with_suffix('.tmp.webm')
            args = [
                '-y', '-loglevel', 'error',
                '-i', str(output_path),
                '-c:v', 'libvpx-vp9',
                '-b:v', '200K',
                '-crf', '35',
                '-pix_fmt', 'yuva420p',
                str(temp_output)
            ]

            if not self._run_ffmpeg(args):
                print("❌ Failed during size reduction")
                return False

            temp_output.replace(output_path)

        print("✅ Done")
        return True

    def find_supported_files(self) -> List[Path]:
        """Find all supported image files in current directory."""
        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            files.extend(Path('.').glob(f'*{ext}'))
            files.extend(Path('.').glob(f'*{ext.upper()}'))
        return sorted(files)
