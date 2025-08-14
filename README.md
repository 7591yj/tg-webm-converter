# Telegram WebM Converter

> This project started off as
> a [shell script](https://github.com/7591yj/converts/blob/main/batch_convert_telegram_webm.sh) for my own personal
> needs
> , so please do expect some rough edges.<br>
> If you find any bugs or have suggestions, please open an issue.
> Thank you for your feedback!

Convert images to Telegram WebM stickers.

## Features

- Convert an image to 100x100 WebM icon (max 32KB)
- Convert images to 512x512 WebM stickers (max 256KB)
- Batch processing support
- Automatic size optimization

## Requirements

- Python 3.8+
- FFmpeg

This application requires [FFmpeg](https://ffmpeg.org/) to be installed on your system.
FFmpeg is open-source software licensed under the LGPLv2.1/GPLv2 (or later).
Please refer to the FFmpeg website for more details on its licensing.

## Installation

```bash
pip install tg-webm-converter
```

## Usage

```bash
# Convert all images in current directory
tg-webm-converter

# Convert specific file to icon, others to stickers
tg-webm-converter -i icon.png

# Convert only one file to sticker
tg-webm-converter -f image.jpg

# Convert only one file to icon
tg-webm-converter --icon-file icon.png
```

## Build from Source

### Prerequisites

- Python 3.8+
- Poetry: `curl -sSL https://install.python-poetry.org | python3 -`
- [FFmpeg](https://ffmpeg.org/): As mentioned above, FFmpeg is a core dependency. Ensure it's installed and accessible
  in your system's PATH.

### Setup

1. Clone the repository

    ```bash
    git clone https://github.com/7591yj/tg-webm-converter.git
    cd tg-webm-converter
    ```

2. Install Dependencies with Poetry

   Poetry will automatically create a virtual environment for the project and install all required dependencies.

    ```bash
    poetry install
    ```

### Running from Source

Once the development environment is set up, you can run the tg-webm-converter command directly using Poetry's run
command:

```bash
# Run the application (same as `tg-webm-converter` if installed via pip)
poetry run tg-webm-converter

# Example: Convert all images in current directory
poetry run tg-webm-converter

# Example: Convert specific file to icon
poetry run tg-webm-converter --icon-file icon.png

# Run tests
poetry run pytest
```

## Future Plans

- Consider a GUI version for easier use.
- Optimize performance for large batch conversions. 
- Explore options for even smaller file sizes.

## License

MIT License