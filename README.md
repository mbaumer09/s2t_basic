# S2T Basic - Minimalist Speech-to-Text for Windows

A lightweight, locally-hosted speech-to-text utility that transcribes your voice directly at your cursor position using OpenAI's Whisper model. Built for Windows with both CLI and GUI interfaces.

## Features

- 🎤 **Push-to-talk recording** with Right Ctrl hotkey
- 🖥️ **GUI interface** with system tray support
- 🚀 **GPU acceleration** support for NVIDIA GPUs
- 🔇 **Smart silence detection** to prevent hallucinations
- 📝 **Transcription history** with session logging
- 🎯 **Multiple Whisper models** (tiny, base, small, medium, large)
- 🔔 **Audio feedback** for recording start/stop
- 🎯 **Window targeting** send text to specific windows even when not focused
- ⚡ **Auto-execute** automatically presses Enter after typing text
- 🗣️ **Voice commands** say "execute mode" to run commands without GUI interaction
- ⚡ **Minimal latency** with optimized processing

## Prerequisites

- Windows 10/11
- Python 3.8+
- ffmpeg (required for Whisper)
- NVIDIA GPU with CUDA support (optional, for faster processing)

## Installation

### 1. Install ffmpeg

#### Option A: Using Chocolatey
```bash
choco install ffmpeg
```

#### Option B: Manual Installation
1. Download from: https://www.gyan.dev/ffmpeg/builds/
2. Download the "full" build
3. Extract and add the `bin` folder to your system PATH

### 2. Clone the repository
```bash
git clone https://github.com/mbaumer09/s2t_basic.git
cd s2t_basic
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Install PyTorch with CUDA support
For GPU acceleration with NVIDIA cards:
```bash
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Usage

### GUI Version (Recommended)
```bash
python speech_to_text_gui.py --model base
```

Features:
- Visual recording indicator
- System tray icon (minimize to tray)
- Microphone selection
- Model switching
- Window targeting (send text to specific windows)
- Auto-execute commands with Enter key
- Transcription history
- Real-time logs

### CLI Version
```bash
python speech_to_text.py --model base
```

### Model Options

| Model | Parameters | VRAM Usage | Speed | Accuracy |
|-------|------------|------------|-------|----------|
| tiny | 39M | ~500MB | Fastest | Lower |
| base | 74M | ~750MB | Fast | Good |
| small | 244M | ~1.5GB | Medium | Better |
| medium | 769M | ~3GB | Slower | Great |
| large | 1550M | ~6GB | Slowest | Best |

### How to Use

1. Run the script with your preferred model
2. Select your microphone (if multiple available)
3. Wait for model to load
4. **Hold Right Ctrl** to record
5. **Release Right Ctrl** to transcribe
6. Text appears at your cursor position

### Voice Commands

Start your speech with these commands for special behavior:

- **"Execute mode [command]"** - Automatically presses Enter after typing
- **"Execute command [command]"** - Same as above
- **"Run command [command]"** - Same as above

Example: Say *"Execute mode python main.py"* to type and run the command automatically.

## Project Structure

```
s2t_basic/
├── speech_to_text.py       # CLI version
├── speech_to_text_gui.py   # GUI version with system tray
├── requirements.txt         # Python dependencies
├── docs/
│   ├── prd.txt            # Product requirements
│   └── followup.md        # Implementation notes
└── logs/                   # Session transcription logs
```

## Features in Detail

### Smart Hallucination Prevention
- Minimum recording duration (0.5s)
- RMS energy-based silence detection
- Filters common Whisper hallucinations ("thank you", "subscribe", etc.)
- Volume threshold checking

### GUI Features
- **System Tray**: Minimize to tray, stays running in background
- **Visual Feedback**: Red recording indicator
- **Model Switching**: Change models without restarting
- **Window Targeting**: Select specific windows to receive text (e.g., always send to Claude Code terminal)
- **Auto-Execute**: Automatically press Enter after typing text (perfect for running voice commands)
- **Voice Commands**: Say "execute mode" at start of speech to auto-run that specific command
- **History**: View all transcriptions with timestamps
- **Audio Toggle**: Enable/disable beep sounds

## Troubleshooting

### No audio recorded
- Check microphone permissions in Windows Settings
- Ensure no other app is using the microphone exclusively
- Try selecting a different microphone in the GUI

### "File not found" error
- Install ffmpeg and ensure it's in your PATH
- Restart your terminal after installing ffmpeg

### Poor transcription quality
- Try a larger model (small, medium, or large)
- Speak clearly and avoid background noise
- Ensure microphone is positioned correctly

## System Requirements

- **Minimum**: 4GB RAM, any CPU
- **Recommended**: 8GB RAM, NVIDIA GPU with 4GB+ VRAM
- **Best Performance**: 16GB RAM, NVIDIA RTX 30/40/50 series

## Privacy

All processing happens locally on your machine. No audio or text is sent to external servers.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Built with [OpenAI Whisper](https://github.com/openai/whisper)
- GUI powered by PyQt6
- Audio processing with sounddevice