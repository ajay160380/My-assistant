# 🤖 J.A.R.V.I.S — Personal AI Voice Assistant

**Just A Rather Very Intelligent System** — An advanced AI voice assistant for macOS, inspired by Iron Man's JARVIS.
---
## ✨ Features

- 🗣️ **Wake Word Detection** — Say "Jarvis" or "Hi Jarvis" to activate
- 🧠 **AI-Powered** — Uses Llama 3.3 70B via Groq for intelligent command parsing
- 🔊 **Siri-Quality Voice** — Apple's premium neural TTS (Rishi voice)
- 🎤 **Hindi/Hinglish/English** — Understands all three languages
- 📱 **App Control** — Open any macOS app by voice
- 🔍 **Web Search** — Google and YouTube search
- 💬 **WhatsApp & iMessage** — Send messages by voice
- 🎵 **Spotify** — Play music by voice
- ⚙️ **System Commands** — Volume, screenshot, battery, lock screen

## 🚀 Setup

### 1. Install Dependencies
```bash
pip install speechrecognition groq pyaudio
```

### 2. Set API Key
```bash
export GROQ_API_KEY='your-groq-api-key'
```
Get your free API key from [Groq Console](https://console.groq.com)

### 3. Run
```bash
python3 jarvis.py
```

## 🎯 Usage

1. Say **"Jarvis"** or **"Hi Jarvis"** to wake up
2. Give your command in Hindi, Hinglish, or English
3. Jarvis will execute and go back to standby

### Example Commands
- "Jarvis, Safari kholo"
- "Jarvis, YouTube pe funny videos search karo"
- "Jarvis, time kya hua hai?"
- "Jarvis, volume badha do"
- "Jarvis, Spotify pe Arijit Singh bajao"

## 👤 Author

**Ajay Vishwakarma**

## 📝 License

MIT License
