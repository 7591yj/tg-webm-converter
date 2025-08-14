import argparse
import sys
from pathlib import Path

from .converter import TgWebMConverter


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert images to Telegram WebM stickers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""   
Examples:
  tg-webm-converter                          # Convert all images in current dir
  tg-webm-converter -i icon.png              # Convert icon.png to icon, others to stickers
  tg-webm-converter -f sticker.jpg           # Convert only sticker.jpg to sticker
  tg-webm-converter --icon-file icon.png     # Convert only icon.png to icon
        """
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-i', '--icon',
        metavar='FILENAME',
        help='Convert FILENAME to 100x100 icon, others to 512x512 stickers'
    )
    group.add_argument(
        '-f', '--file',
        metavar='FILENAME',
        help='Convert only FILENAME to 512x512 sticker'
    )
    group.add_argument(
        '--icon-file',
        metavar='FILENAME',
        help='Convert only FILENAME to 100x100 icon'
    )

    parser.add_argument(
        '-o', '--output',
        default='./webm',
        help='Output directory (default: ./webm)'
    )

    args = parser.parse_args()

    # Validate file existence
    files_to_check = [args.icon, args.file, args.icon_file]
    for file_arg in files_to_check:
        if file_arg and not Path(file_arg).exists():
            print(f"❌ Error: File '{file_arg}' does not exist")
            sys.exit(1)

    converter = TgWebMConverter(args.output)

    try:
        if args.icon_file:
            # Only convert single file to icon
            success = converter.convert_to_icon(args.icon_file)
            sys.exit(0 if success else 1)

        elif args.file:
            # Only convert single file to sticker
            success = converter.convert_to_sticker(args.file)
            sys.exit(0 if success else 1)

        else:
            # Convert all files in directory
            files = converter.find_supported_files()

            if not files:
                print("No supported image files found.")
                sys.exit(0)

            total = len(files)
            successful = 0

            for i, file_path in enumerate(files, 1):
                print(f"[{i:2d}/{total:2d}] ", end="")

                if args.icon and str(file_path) == args.icon:
                    success = converter.convert_to_icon(str(file_path))
                else:
                    success = converter.convert_to_sticker(str(file_path))

                if success:
                    successful += 1

            print(f"🎉 Conversion complete! {successful}/{total} files converted successfully!")
            print(f"Files saved in {converter.output_dir}/")

            if successful < total:
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n❌ Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
