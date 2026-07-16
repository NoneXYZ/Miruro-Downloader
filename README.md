# Miruro VLC CLI

A terminal-based Python CLI for searching, parsing, downloading, and streaming anime from the Miruro.tv API wrapper. The app renders fast Rich-powered terminal tables, resolves episode/provider streams, and can launch HLS streams directly in VLC with the required MRL-level HTTP referrer binding.

The VLC integration is designed for streams that reject normal playback without a valid `Referer` header. Instead of relying on browser playback or CORS-sensitive clients, the CLI passes the stream URL directly to VLC and binds the referrer as a local media resource locator option.

## Features

- Fast terminal UI with Rich tables and panels
- Episode mapping across available providers and language tracks
- Download queue support for single episodes or full seasons
- Smart quality selector support for common HLS renditions such as 1080p, 720p, and 360p
- Direct VLC launching for HLS streams
- Automated VLC MRL header binding with `:http-referrer=...`
- Generic local configuration through environment variables and relative project paths

## Requirements

- Python 3.10 or newer
- VLC media player installed locally
- Internet access for the Miruro.tv API wrapper

Install VLC from the official VLC website or your operating system package manager. On Windows, a standard installation under `%ProgramFiles%` or `%ProgramFiles(x86)%` is supported. On macOS, the default `/Applications` install is supported. On Linux, make sure `vlc` is available on `PATH`.

## Installation

Clone or download the project into any local folder:

```powershell
git clone git@github.com:NoneXYZ/Miruro-Downloader.git
cd Miruro-Downloader
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Configuration

The app can run with its default Miruro.tv wrapper settings. Optional runtime configuration can be placed in a local `.env` file:

```env
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

Keep `.env`, generated queues, temporary files, and downloaded media out of version control.

## Usage

Start the terminal app:

```powershell
python mapper_terminal.py
```

Main menu:

```text
[1] Map Anime
[2] Add/Download Anime
[3] Start Queue (episodes.json)
[4] Stream Anime (VLC)
[0] Exit
```

To stream directly in VLC:

1. Choose option `4`.
2. Paste a Miruro watch link.
3. Select an episode, language, and provider using the table output.
4. Example of a selection like:

```text
12 sub kiwi
```

The app resolves the selected episode source, extracts the first HLS stream URL and referrer, then starts VLC with:

```text
vlc <stream-url> :http-referrer=<referer-url> --meta-title=<title> --network-caching=1500
```

## Project Layout

```text
.
├── core/
│   ├── client.py
│   ├── codec.py
│   └── config.py
├── downloader.py
├── helper.py
├── mapper_terminal.py
├── requirements.txt
└── README.md
```

## Notes

This project is intended as a personal CLI wrapper and playback helper. Use it responsibly and only with media sources you are authorized to access.
