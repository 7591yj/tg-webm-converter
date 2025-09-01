import argparse
import logging.handlers
import sys

from tg_webm_converter.runner import ConversionRunner


def parse_arguments():
    """Parses CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Convert images to Telegram WebM stickers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tg-webm-converter                          # Convert all images in current dir
  tg-webm-converter -i icon.png              # Convert icon.png to icon, others to stickers
  tg-webm-converter -f sticker.jpg           # Convert only sticker.jpg to sticker
  tg-webm-converter --icon-file icon.png     # Convert only icon.png to icon
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-i",
        "--icon",
        metavar="FILENAME",
        help="Convert FILENAME to 100x100 icon, others to 512x512 stickers",
    )
    group.add_argument(
        "-f",
        "--file",
        metavar="FILENAME",
        help="Convert only FILENAME to 512x512 sticker",
    )
    group.add_argument(
        "--icon-file",
        metavar="FILENAME",
        help="Convert only FILENAME to 100x100 icon",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="./webm",
        help="Output directory (default: ./webm)",
    )

    return parser.parse_args()


def main():
    """Main CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stdout,
    )
    args = parse_arguments()

    try:
        runner = ConversionRunner(args)
        success = runner.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logging.info("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logging.error("An error occurred: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
