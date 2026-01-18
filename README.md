# SayLess 🎙➡️🎬

SayLess is an intelligent Telegram bot designed for high-speed communication. It converts long voice messages into concise, high-impact "soundbites" and automatically reacts with an emoji that matches the speaker's emotional tone.

---

## 🚀 Key Features
* Audio Transcription: Converts speech to text using Google's Speech Recognition (optimized for en-SG).
* Emotion Detection: Analyzes the transcript locally to determine the speaker's mood (Joy, Anger, Sadness, etc.).
* Soundbite Generation: Automatically trims and processes the original audio into a highlight reel based on extracted keywords.
* Native Reactions: Uses Telegram's native reaction system to tag generated soundbites with emotional metadata.

---

## 🛠 The Audio Pipeline
The bot handles a complex audio transformation process in real-time:
1.  Ingestion: Downloads Telegram .ogg (Opus) voice files.
2.  Transcoding: Uses FFmpeg and PyDub to convert compressed .ogg to .wav for transcription.
3.  Analysis: Feeds the .wav file into the SpeechRecognition engine.
4.  Synthesis: The soundbite_generator extracts key segments to create a new, shorter .ogg voice message.
5.  Cleanup: Automatically wipes all temporary files (.ogg, .wav) after processing to ensure data privacy and save disk space.

---

## ⚙️ Setup & Installation

### 1. System Requirements
You must have FFmpeg installed for the audio conversion logic to work:
* Windows: choco install ffmpeg
* Mac: brew install ffmpeg

### 2. Environment Configuration
Create a .env file in the root directory:
```env
BOT_TOKEN=your_telegram_bot_token
FREESOUND_API_KEY=your_freesound_api_key
