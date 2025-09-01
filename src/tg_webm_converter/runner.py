import logging
from pathlib import Path

from tg_webm_converter import TgWebMConverter


class ConversionRunner:
    """Orchestrates the file conversion process, based on the CLI arguments."""

    def __init__(self, args):
        """
        Initializes the runner with parsed CLI arguments.

        :param args: argparse.Namespace object with parsed CLI arguments
        """
        self.args = args
        self.converter = TgWebMConverter(args.output)

    def run(self) -> bool:
        """
        Executes the main conversion logic.

        :return: True if all operations completed successfully, False otherwise
        """
        if not self._validate_inputs():
            return False

        if self.args.icon_file:
            return self._run_single_icon_conversion()
        elif self.args.file:
            return self._run_single_sticker_conversion()
        else:
            return self._run_batch_conversion()

    def _validate_inputs(self) -> bool:
        """Validates that specified input files exist."""
        files_to_check = [self.args.icon, self.args.icon_file, self.args.file]
        for file_arg in files_to_check:
            if file_arg and not Path(file_arg).exists():
                logging.error("Input file not found: %s", file_arg)
                return False
        return True

    def _run_single_icon_conversion(self) -> bool:
        """Runs the conversion process for a single icon file."""
        logging.info("Converting icon %s to a 100x100 icon...", self.args.icon_file)
        return self.converter.convert_to_icon(self.args.icon_file)

    def _run_single_sticker_conversion(self) -> bool:
        """Runs the conversion process for a single sticker file."""
        logging.info("Converting sticker %s to a 512x512 sticker...", self.args.file)
        return self.converter.convert_to_sticker(self.args.file)

    def _run_batch_conversion(self) -> bool:
        """Runs the conversion process for a batch of files."""
        logging.info("Finding supported image files in directory %s...", self.args.output)
        files = self.converter.find_supported_files()

        if not files:
            logging.warning("No supported image files found.")
            return True

        total = len(files)
        successful = 0
        logging.info("Found %d files to convert.", total)

        for i, file_path in enumerate(files, 1):
            is_icon = self.args.icon and str(file_path) == self.args.icon
            log_prefix = f"[{i:2d}/{total:2d}] "

            if is_icon:
                logging.info("%s Converting %s to icon...", log_prefix, file_path)
                success = self.converter.convert_to_icon(str(file_path))
            else:
                logging.info("%s Converting %s to sticker...", log_prefix, file_path)
                success = self.converter.convert_to_sticker(str(file_path))

            if success:
                successful += 1

        logging.info("-" * 20)
        logging.info("Conversion complete! %d/%d files converted successfully!", successful, total)
        logging.info("Files saved in: %s/", self.converter.output_dir)

        return successful == total
