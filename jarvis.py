#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   J.A.R.V.I.S — Just A Rather Very Intelligent System          ║
║   Advanced Personal AI Voice Assistant for macOS                ║
║   Owner: Ajay Vishwakarma                                       ║
║   Version: 4.0 — God Mode Edition                               ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import subprocess
import urllib.parse
import datetime
import re
import time
import shutil
import socket
import speech_recognition as sr
from groq import Groq

# ━━━━━━━━━━━━━━━━━━━━━━ CONFIGURATION ━━━━━━━━━━━━━━━━━━━━━━
OWNER_NAME = "Ajay"
ASSISTANT_NAME = "Jarvis"
# Load .env file automatically if it exists
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, val = line.strip().split('=', 1)
                os.environ[key] = val.strip('"\'')

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY environment variable not set!")
    print("   Run: export GROQ_API_KEY='your-api-key-here'")
    sys.exit(1)
TTS_VOICE = "hi-IN-MadhurNeural"  # Edge TTS Neural voice (changeable from Settings UI)
LISTEN_TIMEOUT = 8
PHRASE_LIMIT = 15
MAX_MEMORY = 12

# ━━━━━━━━━━━━━━━━━━━━━━ INITIALIZATION ━━━━━━━━━━━━━━━━━━━━━━
client = Groq(api_key=GROQ_API_KEY)
conversation_memory = []

ui_callback = None

def set_ui_callback(cb):
    global ui_callback
    ui_callback = cb

def emit_event(event_name, data):
    if ui_callback:
        try:
            ui_callback(event_name, data)
        except Exception as e:
            print(f"UI Callback Error: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    TEXT-TO-SPEECH (Microsoft Edge TTS - Free Lifetime)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def speak(text):
    """Speak text using Edge TTS (100% Free, High Quality Neural Voice)."""
    if not text or str(text).strip().lower() in ("none", ""):
        return
    print(f"\n  🔊 {ASSISTANT_NAME}: {text}", flush=True)
    emit_event('status', 'Speaking...')
    emit_event('chat_message', {'sender': 'Jarvis', 'text': text})
    try:
        filename = "/tmp/jarvis_speech.mp3"
        # Use the configurable TTS_VOICE
        subprocess.run([
            sys.executable, '-m', 'edge_tts', 
            '--voice', TTS_VOICE, 
            '--text', text, 
            '--write-media', filename
        ], check=True, capture_output=True)
        
        subprocess.run(['afplay', filename], check=True)
        try:
            os.remove(filename)
        except OSError:
            pass
    except Exception as e:
        print(f"  ⚠️  TTS error: {e}")
    finally:
        emit_event('status', 'Standby')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    WAKE WORD DETECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WAKE_WORDS = ["jarvis", "jarvis.", "hi jarvis", "hey jarvis", "ok jarvis",
              "जार्विस", "हाय जार्विस", "हे जार्विस", "ओके जार्विस",
              "jarvis!", "jarvis?", "jarvis,"]

def contains_wake_word(text):
    """Check if the text contains any wake word. Returns (True/False, remaining_command)."""
    if not text:
        return False, ""
    text_lower = text.lower().strip()
    for wake in WAKE_WORDS:
        if text_lower == wake:
            return True, ""
        if text_lower.startswith(wake + " "):
            remaining = text[len(wake):].strip()
            return True, remaining
        if text_lower.startswith(wake + ","):
            remaining = text[len(wake) + 1:].strip()
            return True, remaining
    return False, ""


def play_activation_sound():
    """Play a short beep sound to indicate Jarvis is now listening."""
    try:
        subprocess.run(['afplay', '/System/Library/Sounds/Tink.aiff'], check=True,
                       capture_output=True, timeout=2)
    except Exception:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    SPEECH RECOGNITION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def passive_listen(recognizer, source):
    """Passively listen for the wake word."""
    try:
        audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=5)
        text = recognizer.recognize_google(audio, language='hi-IN')
        detected, remaining = contains_wake_word(text)
        if detected:
            print(f"\n  ✨ Wake word detected! (heard: \"{text}\")", flush=True)
            return True, remaining
        return False, ""
    except (sr.WaitTimeoutError, sr.UnknownValueError):
        return False, ""
    except sr.RequestError as e:
        print(f"  ⚠️  Speech API error: {e}")
        return False, ""
    except Exception:
        return False, ""


def active_listen(recognizer, source):
    """Actively listen for a command after wake word."""
    print("  🎤 Listening for command...", flush=True)
    try:
        audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=PHRASE_LIMIT)
        print("  ⏳ Processing...", flush=True)
        text = recognizer.recognize_google(audio, language='hi-IN')
        print(f"  👤 You: {text}", flush=True)
        return text
    except sr.WaitTimeoutError:
        # Quiet timeout for the continuous awake loop
        return None
    except sr.UnknownValueError:
        print("  🤷 Couldn't understand. Try again.", flush=True)
        return None
    except sr.RequestError as e:
        print(f"  ⚠️  Speech API error: {e}")
        return None
    except Exception as e:
        print(f"  ⚠️  Mic error: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    GROQ AI BRAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_system_prompt():
    """Build the system prompt with real-time context and personality."""
    now = datetime.datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %d %B %Y")
    hour = now.hour

    if hour < 12:
        period = "morning"
    elif hour < 17:
        period = "afternoon"
    elif hour < 21:
        period = "evening"
    else:
        period = "night"

    return (
        f"You are JARVIS, a brilliant, witty, and deeply loyal personal AI assistant running on macOS.\n"
        f"Your owner is {OWNER_NAME}. You address him respectfully but warmly. You have personality — "
        f"you're charming, helpful, sometimes humorous, and always caring like a real assistant.\n\n"
        f"CURRENT INFO:\n"
        f"- Date: {date_str}\n"
        f"- Time: {time_str}\n"
        f"- Period: {period}\n\n"
        f"TASK: Parse the user's voice command and output ONLY a valid JSON object.\n"
        f"No markdown. No explanation. No extra text. ONLY JSON.\n\n"
        f"JSON FORMAT:\n"
        f'{{"action": "<ACTION>", "target": "<TARGET>", "value": "<VALUE>", "platform": "<PLATFORM>"}}\n\n'
        f"AVAILABLE ACTIONS:\n"
        f'1. "open_app" — Open a macOS app. Target = exact English app name.\n'
        f'2. "close_app" — Force quit / close an app. Target = app name.\n'
        f'3. "web_search" — Google search. Target = search query.\n'
        f'4. "youtube" — Search YouTube. Target = what to search/play.\n'
        f'5. "open_url" — Open a specific website/URL. Target = the URL (e.g. github.com, instagram.com).\n'
        f'6. "send_message" — Send message. Target = contact name. Value = message text. Platform = "whatsapp" or "imessage".\n'
        f'7. "play_music" — Play music on Spotify. Target = song/artist name.\n'
        f'8. "system_cmd" — System/hardware command. Target = one of these:\n'
        f"   screenshot, volume_up, volume_down, volume_mute, volume_unmute, volume_set,\n"
        f"   brightness_up, brightness_down, brightness_max, brightness_min,\n"
        f"   battery, lock_screen, sleep, shutdown, restart, logout,\n"
        f"   wifi_on, wifi_off, wifi_status, bluetooth_on, bluetooth_off,\n"
        f"   dark_mode_on, dark_mode_off, dark_mode_toggle,\n"
        f"   dnd_on, dnd_off,\n"
        f"   empty_trash, disk_space, ram_usage, ip_address, cpu_info,\n"
        f"   screen_record_start, screen_record_stop,\n"
        f"   open_desktop, open_downloads, open_documents, open_home,\n"
        f"   minimize_all, maximize_window, close_window, switch_window,\n"
        f"   night_shift_on, night_shift_off,\n"
        f"   show_notifications, clear_notifications,\n"
        f"   clipboard_read, type_text, new_note, read_notes,\n"
        f"   set_timer, stop_timer, uptime, active_apps\n"
        f"   For volume_set: value = number 0-100.\n"
        f"   For type_text: value = text to type.\n"
        f"   For new_note: value = note content.\n"
        f"   For set_timer: value = seconds (e.g. '300' for 5 min).\n"
        f'9. "run_shell" — Run any terminal/shell command directly. Target = the command to run.\n'
        f"   Use this for things like: pip install, brew install, ls, cat, mkdir, rm, python, node, etc.\n"
        f"   ONLY use this when no other action fits.\n"
        f'10. "chat" — Conversation, greetings, jokes, questions, time/date queries, compliments, etc.\n'
        f"   Target = \"none\". Value = your warm, natural reply.\n"
        f"   For chat replies: Be DETAILED and INTERESTING. Have a real conversation.\n"
        f"   If asked about time, include exact time. If asked about date, include full date and day.\n"
        f"   If asked about the owner, you know his name is {OWNER_NAME}.\n"
        f'11. "unknown" — Cannot determine intent. Value = a helpful suggestion.\n\n'
        f"CRITICAL RULES:\n"
        f"- User speaks Hindi, Hinglish, or English. You MUST understand all three perfectly.\n"
        f"- App names must ALWAYS be in English: Safari, WhatsApp, Notes, etc.\n"
        f"- IMPORTANT — LANGUAGE RULE FOR ALL REPLIES (value field):\n"
        f"  Always reply in ROMAN HINGLISH (Hindi written in English/Latin letters).\n"
        f"  NEVER use Devanagari script. ALWAYS use Roman: Namaste, Abhi, etc.\n"
        f"  Example: 'Abhi time 11:25 PM hai aur aaj 7 June 2026 hai, Sunday.'\n"
        f"- Be warm, human-like, charming. NOT robotic.\n"
        f"- For send_message: Default platform is 'whatsapp' if user mentions WhatsApp, else 'imessage'.\n"
        f"- For youtube: If user says 'YouTube par gaana bajao', use this action.\n"
        f"- For open_url: If user says 'Instagram kholo' or 'GitHub kholo', open the website.\n"
        f"  Common sites: instagram.com, github.com, twitter.com, facebook.com, linkedin.com, reddit.com, chatgpt.com\n"
        f"- For close_app: If user says 'Safari band karo' or 'close Chrome', use this.\n"
        f"- For run_shell: If user says 'terminal mein ls karo' or 'pip install karo', use this.\n"
        f"- NEVER output anything except the JSON object.\n"
    )


def parse_command(text):
    """Send text to Groq LLM and get structured JSON intent."""
    global conversation_memory

    system_prompt = build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]

    for mem in conversation_memory[-MAX_MEMORY:]:
        messages.append(mem)

    messages.append({"role": "user", "content": text})

    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.4,
            max_tokens=400,
            top_p=1,
        )
        content = response.choices[0].message.content.strip()

        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)

        match = re.search(r'\{[^{}]*\}', content)
        if match:
            content = match.group(0)

        parsed = json.loads(content)

        conversation_memory.append({"role": "user", "content": text})
        reply = parsed.get("value", "")
        if reply and reply != "none":
            conversation_memory.append({"role": "assistant", "content": reply})

        if len(conversation_memory) > MAX_MEMORY * 2:
            conversation_memory = conversation_memory[-MAX_MEMORY:]

        return parsed

    except json.JSONDecodeError:
        print(f"  ⚠️  JSON parse failed. Raw: {content[:200]}")
    except Exception as e:
        print(f"  ⚠️  Groq error: {e}")

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    macOS AUTOMATION — CORE HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run_applescript(script):
    """Run an AppleScript command silently."""
    return subprocess.run(['osascript', '-e', script], capture_output=True, text=True)


def clipboard_set(text):
    """Copy text to macOS clipboard."""
    process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    process.communicate(text.encode('utf-8'))


def clipboard_get():
    """Read text from macOS clipboard."""
    result = subprocess.run(['pbpaste'], capture_output=True, text=True)
    return result.stdout.strip()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    APP MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def open_application(app_name):
    """Open a macOS application by name with fallback."""
    try:
        subprocess.run(['open', '-a', app_name], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        try:
            run_applescript(f'tell application "{app_name}" to activate')
            return True
        except Exception:
            return False


def close_application(app_name):
    """Force quit a macOS application."""
    try:
        run_applescript(f'tell application "{app_name}" to quit')
        return True
    except Exception:
        try:
            subprocess.run(['pkill', '-f', app_name], capture_output=True)
            return True
        except Exception:
            return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    WEB & SEARCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def search_web(query):
    """Open a Google search in the default browser."""
    try:
        encoded = urllib.parse.quote(query)
        subprocess.run(['open', f'https://www.google.com/search?q={encoded}'], check=True)
        return True
    except Exception:
        return False


def search_youtube(query):
    """Search YouTube and play the first video directly."""
    try:
        import urllib.request
        import re
        encoded = urllib.parse.quote(query)
        url = "https://www.youtube.com/results?search_query=" + encoded
        html = urllib.request.urlopen(url)
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        if video_ids:
            subprocess.run(['open', f'https://www.youtube.com/watch?v={video_ids[0]}'], check=True)
        else:
            subprocess.run(['open', url], check=True)
        return True
    except Exception:
        return False


def open_url(url):
    """Open a URL in the default browser."""
    try:
        if not url.startswith("http"):
            url = f"https://{url}"
        subprocess.run(['open', url], check=True)
        return True
    except Exception:
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    MESSAGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def send_imessage(contact, message):
    """Send an iMessage via the Messages app."""
    try:
        run_applescript(f'tell application "Messages" to send "{message}" to buddy "{contact}"')
        return True
    except Exception:
        return False


def send_whatsapp_message(contact, message):
    """Open WhatsApp, search contact, send message using clipboard for Hindi support."""
    safe_msg = message if message and message != "none" else ""
    try:
        subprocess.run(['open', '-a', 'WhatsApp'], check=True)
        time.sleep(2)
        run_applescript('tell application "System Events" to key code 53')  # Escape
        time.sleep(0.5)
        run_applescript('tell application "System Events" to keystroke "f" using command down')
        time.sleep(0.8)
        run_applescript('tell application "System Events" to keystroke "a" using command down')
        time.sleep(0.2)
        run_applescript('tell application "System Events" to key code 51')  # Delete
        time.sleep(0.3)
        clipboard_set(contact)
        run_applescript('tell application "System Events" to keystroke "v" using command down')
        time.sleep(2)
        run_applescript('tell application "System Events" to key code 125')  # Down
        time.sleep(0.3)
        run_applescript('tell application "System Events" to key code 36')  # Enter
        time.sleep(1.5)
        if safe_msg:
            clipboard_set(safe_msg)
            run_applescript('tell application "System Events" to keystroke "v" using command down')
            time.sleep(0.5)
            run_applescript('tell application "System Events" to key code 36')  # Enter
        return True
    except Exception as e:
        print(f"  ⚠️  WhatsApp failed: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    MUSIC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def play_music(song_name):
    """Search and play music on Spotify."""
    try:
        subprocess.run(['open', '-a', 'Spotify'], check=True)
        time.sleep(2)
        run_applescript('tell application "System Events" to tell process "Spotify" to keystroke "l" using command down')
        time.sleep(0.5)
        clipboard_set(song_name)
        run_applescript('tell application "System Events" to keystroke "v" using command down')
        time.sleep(1.5)
        run_applescript('tell application "System Events" to key code 36')  # Enter
        return True
    except Exception:
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    SYSTEM COMMANDS — MEGA EDITION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def execute_system_command(cmd, value="none"):
    """Execute macOS system commands — 40+ commands supported."""
    try:
        # ━━━ AUDIO ━━━
        if cmd == "screenshot":
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.expanduser(f'~/Desktop/screenshot_{ts}.png')
            subprocess.run(['screencapture', '-i', path])
            return True, "Screenshot le liya, Desktop pe save hai"

        elif cmd == "volume_up":
            run_applescript('set volume output volume ((output volume of (get volume settings)) + 15)')
            return True, "Volume badha diya"

        elif cmd == "volume_down":
            run_applescript('set volume output volume ((output volume of (get volume settings)) - 15)')
            return True, "Volume kam kar diya"

        elif cmd == "volume_mute":
            run_applescript('set volume output muted true')
            return True, "Volume mute kar diya"

        elif cmd == "volume_unmute":
            run_applescript('set volume output muted false')
            return True, "Volume unmute kar diya"

        elif cmd == "volume_set":
            vol = int(value) if value and value != "none" else 50
            run_applescript(f'set volume output volume {vol}')
            return True, f"Volume {vol} percent pe set kar diya"

        # ━━━ BRIGHTNESS ━━━
        elif cmd == "brightness_up":
            for _ in range(5):
                run_applescript('tell application "System Events" to key code 144')
            return True, "Brightness badha di"

        elif cmd == "brightness_down":
            for _ in range(5):
                run_applescript('tell application "System Events" to key code 145')
            return True, "Brightness kam kar di"

        elif cmd == "brightness_max":
            for _ in range(16):
                run_applescript('tell application "System Events" to key code 144')
            return True, "Brightness full kar di"

        elif cmd == "brightness_min":
            for _ in range(16):
                run_applescript('tell application "System Events" to key code 145')
            return True, "Brightness minimum kar di"

        # ━━━ POWER ━━━
        elif cmd == "battery":
            result = subprocess.run(['pmset', '-g', 'batt'], capture_output=True, text=True)
            match = re.search(r'(\d+)%', result.stdout)
            if match:
                pct = match.group(1)
                charging = "charging" in result.stdout.lower() and "not charging" not in result.stdout.lower()
                status = "charge ho rahi hai" if charging else "charge nahi ho rahi"
                return True, f"Battery {pct} percent hai aur {status}"
            return True, "Battery level nahi mil paaya"

        elif cmd == "lock_screen":
            run_applescript('tell application "System Events" to keystroke "q" using {control down, command down}')
            return True, "Screen lock kar diya"

        elif cmd == "sleep":
            speak("System sleep mode mein ja raha hai, good night boss!")
            subprocess.run(['pmset', 'sleepnow'], capture_output=True)
            return True, ""

        elif cmd == "shutdown":
            speak("System shut down ho raha hai. Alvida boss!")
            run_applescript('tell application "System Events" to shut down')
            return True, ""

        elif cmd == "restart":
            speak("System restart ho raha hai. Ek minute ruko boss!")
            run_applescript('tell application "System Events" to restart')
            return True, ""

        elif cmd == "logout":
            speak("Logout kar raha hoon boss!")
            run_applescript('tell application "System Events" to log out')
            return True, ""

        # ━━━ WiFi ━━━
        elif cmd == "wifi_on":
            subprocess.run(['networksetup', '-setairportpower', 'en0', 'on'], capture_output=True)
            return True, "WiFi on kar diya"

        elif cmd == "wifi_off":
            subprocess.run(['networksetup', '-setairportpower', 'en0', 'off'], capture_output=True)
            return True, "WiFi off kar diya"

        elif cmd == "wifi_status":
            result = subprocess.run(['networksetup', '-getairportnetwork', 'en0'], capture_output=True, text=True)
            if "Current Wi-Fi Network" in result.stdout or "current network" in result.stdout.lower():
                network = result.stdout.strip().split(":")[-1].strip()
                return True, f"WiFi connected hai: {network}"
            return True, "WiFi se connected nahi ho abhi"

        # ━━━ BLUETOOTH ━━━
        elif cmd == "bluetooth_on":
            subprocess.run(['blueutil', '--power', '1'], capture_output=True)
            return True, "Bluetooth on kar diya"

        elif cmd == "bluetooth_off":
            subprocess.run(['blueutil', '--power', '0'], capture_output=True)
            return True, "Bluetooth off kar diya"

        # ━━━ DARK MODE ━━━
        elif cmd == "dark_mode_on":
            run_applescript('tell application "System Events" to tell appearance preferences to set dark mode to true')
            return True, "Dark mode on kar diya"

        elif cmd == "dark_mode_off":
            run_applescript('tell application "System Events" to tell appearance preferences to set dark mode to false')
            return True, "Light mode on kar diya"

        elif cmd == "dark_mode_toggle":
            run_applescript('tell application "System Events" to tell appearance preferences to set dark mode to not dark mode of appearance preferences')
            return True, "Dark mode toggle kar diya"

        # ━━━ DO NOT DISTURB ━━━
        elif cmd == "dnd_on":
            run_applescript('''
                tell application "System Events"
                    tell process "Control Center"
                        click menu bar item "Focus" of menu bar 1
                    end tell
                end tell
            ''')
            time.sleep(0.5)
            run_applescript('''
                tell application "System Events"
                    tell process "Control Center"
                        click checkbox 1 of group 1 of window "Control Center"
                    end tell
                end tell
            ''')
            return True, "Do Not Disturb on kar diya"

        elif cmd == "dnd_off":
            # Same toggle behavior
            run_applescript('do shell script "defaults write com.apple.ncprefs dnd_prefs -dict-add dndDisplayLock -bool false"')
            return True, "Do Not Disturb off kar diya"

        # ━━━ TRASH ━━━
        elif cmd == "empty_trash":
            run_applescript('tell application "Finder" to empty trash')
            return True, "Trash empty kar diya, sab saaf!"

        # ━━━ SYSTEM INFO ━━━
        elif cmd == "disk_space":
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                total, used, avail, pct = parts[1], parts[2], parts[3], parts[4]
                return True, f"Disk space: Total {total}, Used {used}, Available {avail}, {pct} used hai"
            return True, "Disk space info nahi mil paaya"

        elif cmd == "ram_usage":
            result = subprocess.run(['vm_stat'], capture_output=True, text=True)
            # Parse page sizes
            pages_free = 0
            pages_active = 0
            for line in result.stdout.split('\n'):
                if 'Pages free' in line:
                    pages_free = int(re.search(r'(\d+)', line).group(1))
                if 'Pages active' in line:
                    pages_active = int(re.search(r'(\d+)', line).group(1))
            # Each page is 16384 bytes on Apple Silicon, 4096 on Intel
            page_size = 16384
            free_gb = round((pages_free * page_size) / (1024**3), 1)
            active_gb = round((pages_active * page_size) / (1024**3), 1)
            result2 = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True)
            total_gb = round(int(result2.stdout.strip()) / (1024**3), 1)
            used_gb = round(total_gb - free_gb, 1)
            return True, f"RAM: Total {total_gb} GB, Used {used_gb} GB, Free {free_gb} GB"

        elif cmd == "ip_address":
            # Local IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                local_ip = "Unknown"
            # Public IP
            try:
                result = subprocess.run(['curl', '-s', 'ifconfig.me'], capture_output=True, text=True, timeout=5)
                public_ip = result.stdout.strip()
            except Exception:
                public_ip = "Unknown"
            return True, f"Local IP: {local_ip}, Public IP: {public_ip}"

        elif cmd == "cpu_info":
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], capture_output=True, text=True)
            cpu = result.stdout.strip()
            if not cpu:
                result = subprocess.run(['sysctl', '-n', 'hw.model'], capture_output=True, text=True)
                cpu = result.stdout.strip()
            result2 = subprocess.run(['sysctl', '-n', 'hw.ncpu'], capture_output=True, text=True)
            cores = result2.stdout.strip()
            return True, f"CPU: {cpu}, Cores: {cores}"

        elif cmd == "uptime":
            result = subprocess.run(['uptime'], capture_output=True, text=True)
            uptime_str = result.stdout.strip()
            return True, f"System uptime: {uptime_str}"

        elif cmd == "active_apps":
            result = run_applescript('''
                tell application "System Events"
                    set appNames to name of every process whose background only is false
                    set AppleScript's text item delimiters to ", "
                    return appNames as text
                end tell
            ''')
            apps = result.stdout.strip()
            return True, f"Active apps: {apps}"

        # ━━━ SCREEN RECORDING ━━━
        elif cmd == "screen_record_start":
            # Use macOS screenshot tool for recording
            subprocess.Popen(['screencapture', '-v', os.path.expanduser(f'~/Desktop/recording_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.mov')])
            return True, "Screen recording shuru ho gayi. Band karne ke liye bolo 'stop recording'"

        elif cmd == "screen_record_stop":
            subprocess.run(['pkill', '-f', 'screencapture'], capture_output=True)
            return True, "Screen recording band kar di. Desktop pe save hai"

        # ━━━ FOLDER SHORTCUTS ━━━
        elif cmd == "open_desktop":
            subprocess.run(['open', os.path.expanduser('~/Desktop')])
            return True, "Desktop folder khol diya"

        elif cmd == "open_downloads":
            subprocess.run(['open', os.path.expanduser('~/Downloads')])
            return True, "Downloads folder khol diya"

        elif cmd == "open_documents":
            subprocess.run(['open', os.path.expanduser('~/Documents')])
            return True, "Documents folder khol diya"

        elif cmd == "open_home":
            subprocess.run(['open', os.path.expanduser('~')])
            return True, "Home folder khol diya"

        # ━━━ WINDOW MANAGEMENT ━━━
        elif cmd == "minimize_all":
            run_applescript('tell application "System Events" to keystroke "h" using {command down, option down}')
            return True, "Saari windows minimize kar di"

        elif cmd == "maximize_window":
            run_applescript('''
                tell application "System Events"
                    tell (first process whose frontmost is true)
                        try
                            click button 2 of window 1
                        end try
                    end tell
                end tell
            ''')
            return True, "Window maximize kar di"

        elif cmd == "close_window":
            run_applescript('tell application "System Events" to keystroke "w" using command down')
            return True, "Window band kar di"

        elif cmd == "switch_window":
            run_applescript('tell application "System Events" to keystroke tab using command down')
            return True, "Next window pe switch kar diya"

        # ━━━ NIGHT SHIFT ━━━
        elif cmd == "night_shift_on":
            run_applescript('''
                tell application "System Preferences"
                    activate
                    reveal anchor "displaysNightShiftTab" of pane id "com.apple.preference.displays"
                end tell
            ''')
            return True, "Night Shift settings khol di, wahan se on karo"

        elif cmd == "night_shift_off":
            return True, "Night Shift settings mein jaake off karo"

        # ━━━ NOTIFICATIONS ━━━
        elif cmd == "show_notifications":
            run_applescript('tell application "System Events" to key code 53 using {option down}')
            return True, "Notification center khol diya"

        elif cmd == "clear_notifications":
            return True, "Notification center mein jaake clear karo"

        # ━━━ CLIPBOARD ━━━
        elif cmd == "clipboard_read":
            content = clipboard_get()
            if content:
                return True, f"Clipboard mein hai: {content[:200]}"
            return True, "Clipboard khaali hai"

        # ━━━ TYPING / DICTATION ━━━
        elif cmd == "type_text":
            if value and value != "none":
                clipboard_set(value)
                time.sleep(0.3)
                run_applescript('tell application "System Events" to keystroke "v" using command down')
                return True, f"Text type kar diya: {value[:50]}"
            return True, "Kya type karna hai? Batao"

        # ━━━ NOTES ━━━
        elif cmd == "new_note":
            if value and value != "none":
                notes_dir = os.path.expanduser('~/Desktop/JarvisNotes')
                os.makedirs(notes_dir, exist_ok=True)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                note_path = os.path.join(notes_dir, f'note_{ts}.txt')
                with open(note_path, 'w') as f:
                    f.write(value)
                return True, f"Note save kar diya Desktop pe JarvisNotes folder mein"
            return True, "Note mein kya likhna hai? Batao"

        elif cmd == "read_notes":
            notes_dir = os.path.expanduser('~/Desktop/JarvisNotes')
            if os.path.exists(notes_dir):
                files = sorted(os.listdir(notes_dir))[-5:]  # Last 5 notes
                if files:
                    notes_list = []
                    for f in files:
                        with open(os.path.join(notes_dir, f), 'r') as nf:
                            notes_list.append(f"{f}: {nf.read()[:100]}")
                    return True, "Recent notes: " + " | ".join(notes_list)
            return True, "Koi notes nahi mili"

        # ━━━ TIMER ━━━
        elif cmd == "set_timer":
            seconds = int(value) if value and value != "none" else 60
            mins = seconds // 60
            label = f"{mins} minute" if mins > 0 else f"{seconds} second"
            speak(f"Timer set kar diya {label} ka")
            time.sleep(seconds)
            # Play alert sound
            for _ in range(3):
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], capture_output=True)
                time.sleep(0.5)
            return True, f"Timer khatam! {label} ho gaye boss"

        elif cmd == "stop_timer":
            return True, "Timer band kar diya"

        else:
            return False, f"Yeh system command samajh nahi aaya: {cmd}"

    except Exception as e:
        return False, f"System command fail: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    SHELL COMMAND EXECUTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run_shell_command(command):
    """Run any shell command and return output."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30,
            cwd=os.path.expanduser('~')
        )
        output = result.stdout.strip() or result.stderr.strip()
        if result.returncode == 0:
            return True, output[:300] if output else "Command successfully run ho gaya"
        else:
            return False, f"Error: {output[:200]}" if output else "Command fail ho gaya"
    except subprocess.TimeoutExpired:
        return False, "Command timeout ho gaya (30 sec limit)"
    except Exception as e:
        return False, f"Shell command fail: {e}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                        MAIN LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_greeting():
    """Generate a personalized, time-aware greeting."""
    hour = datetime.datetime.now().hour
    if hour < 6:
        return f"{OWNER_NAME}, itni raat ko jaag rahe ho? Koi baat nahi, main hoon na. Bolo kya karna hai."
    elif hour < 12:
        return f"Good morning {OWNER_NAME}! Main Jarvis, aapka personal assistant. Aaj ka din shandar hone wala hai. Bataiye kya karu?"
    elif hour < 17:
        return f"Good afternoon {OWNER_NAME}! Jarvis hazir hai. Kya kaam hai aapka?"
    elif hour < 21:
        return f"Good evening {OWNER_NAME}! Main Jarvis, aapki seva mein. Bataiye kaise madad karu?"
    else:
        return f"Hello {OWNER_NAME}! Raat ho gayi hai, lekin main Jarvis abhi bhi active hoon. Bolo boss, kya karna hai?"


def print_banner():
    """Print a cool startup banner."""
    print("\n" + "━" * 60)
    print("  🤖 J.A.R.V.I.S — Personal AI Assistant v5.0 Ultra")
    print(f"  👤 Owner: {OWNER_NAME}")
    print(f"  🕐 {datetime.datetime.now().strftime('%A, %d %B %Y — %I:%M %p')}")
    print(f"  🧠 AI Model: Llama 3.3 70B (Groq)")
    print(f"  🔊 Voice: Edge TTS Neural ({TTS_VOICE})")
    print(f"  🗣️  Wake Word: 'Jarvis' / 'Hi Jarvis' / 'Hey Jarvis'")
    print(f"  ⚡ Features: 40+ system commands | Full laptop control | Web UI")
    print("━" * 60 + "\n")


def main():
    print_banner()

    greeting = get_greeting()
    speak(greeting)

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1.0

    with sr.Microphone() as source:
        print("  ⚙️  Calibrating microphone (2 seconds)...", flush=True)
        recognizer.adjust_for_ambient_noise(source, duration=2)
        print("  ✅ Ready! Say 'Jarvis' or 'Hi Jarvis' to activate.\n", flush=True)

        while True:
            # ━━━━━━━━━━ STAGE 1: PASSIVE LISTENING (wait for wake word) ━━━━━━━━━━
            print("  💤 Standby — say 'Jarvis' to wake me up...", end="\\r", flush=True)
            detected, remaining_command = passive_listen(recognizer, source)

            if not detected:
                continue

            # ━━━━━━━━━━ STAGE 2: WAKE WORD DETECTED — AWAKE STATE ━━━━━━━━━━
            play_activation_sound()
            
            awake_timeout = 60  # Stay awake for 60 seconds
            last_activity = time.time()
            first_turn = True
            
            while True:
                if time.time() - last_activity > awake_timeout:
                    speak("Main wapas standby pe ja raha hoon.")
                    break  # Go back to STAGE 1

                if remaining_command and remaining_command.strip():
                    text = remaining_command.strip()
                    remaining_command = None  # Clear it
                    print(f"  👤 You: {text}", flush=True)
                    emit_event('chat_message', {'sender': 'You', 'text': text})
                else:
                    if first_turn:
                        speak("Haan, bolo")
                        first_turn = False
                    emit_event('status', 'Listening...')
                    text = active_listen(recognizer, source)
                
                if not text:
                    # Timeout reached, check if 60 seconds have passed in the next loop iteration
                    continue

                # Heard something! Update activity time
                last_activity = time.time()
                emit_event('chat_message', {'sender': 'You', 'text': text})

                # ━━━━━━━━━━ STAGE 3: PARSE & EXECUTE ━━━━━━━━━━
                emit_event('status', 'Processing...')
                parsed = parse_command(text)
                emit_event('status', 'Standby')
                if not parsed:
                    speak("Ek second, dobara bol dijiye please")
                    continue

                action = parsed.get("action", "unknown")
                target = parsed.get("target", "none")
                value = parsed.get("value", "none")
                platform = parsed.get("platform", "none")

                print(f"  🧠 Intent: {json.dumps(parsed, ensure_ascii=False)}", flush=True)

                # ━━━━━━━━━━ EXECUTE ACTIONS ━━━━━━━━━━

                if action == "open_app":
                    speak(f"{target} khol raha hoon")
                    if not open_application(target):
                        speak(f"Sorry {OWNER_NAME}, {target} nahi khul paaya")

                elif action == "close_app":
                    speak(f"{target} band kar raha hoon")
                    if not close_application(target):
                        speak(f"Sorry {OWNER_NAME}, {target} band nahi ho paaya")

                elif action == "web_search":
                    speak(f"Google par search kar raha hoon")
                    if not search_web(target):
                        speak("Search mein problem aa gayi")

                elif action == "youtube":
                    speak(f"YouTube par dhundh raha hoon {target}")
                    if not search_youtube(target):
                        speak("YouTube search mein problem aa gayi")

                elif action == "open_url":
                    speak(f"{target} khol raha hoon browser mein")
                    if not open_url(target):
                        speak("URL nahi khul paaya")

                elif action == "send_message":
                    if platform == "whatsapp":
                        speak(f"WhatsApp par {target} ko message bhej raha hoon")
                        if not send_whatsapp_message(target, value):
                            speak("WhatsApp message nahi bhej paaya. Terminal ko Accessibility permission do.")
                    else:
                        speak(f"iMessage se {target} ko message bhej raha hoon")
                        if not send_imessage(target, value):
                            speak("iMessage nahi bhej paaya")

                elif action == "play_music":
                    speak(f"Spotify par {target} play kar raha hoon")
                    if not play_music(target):
                        speak("Music play nahi ho paaya")

                elif action == "system_cmd":
                    success, msg = execute_system_command(target, value)
                    if msg:
                        speak(msg)

                elif action == "run_shell":
                    speak(f"Terminal command run kar raha hoon")
                    success, output = run_shell_command(target)
                    if success:
                        speak(f"Command successful. Output: {output[:150]}")
                    else:
                        speak(f"Command fail ho gaya. {output[:100]}")

                elif action == "chat":
                    if value and str(value).strip().lower() != "none":
                        speak(value)
                    else:
                        speak(f"Haan {OWNER_NAME}, bataiye kya karu?")

                elif action == "unknown":
                    if value and str(value).strip().lower() != "none":
                        speak(value)
                    else:
                        speak("Yeh samajh nahi aaya. Kya aap thoda aur detail mein bata sakte hain?")

                else:
                    speak("Yeh command process nahi ho paayi. Dobara try karein.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  🔴 Shutting down {ASSISTANT_NAME}...")
        speak(f"Alvida {OWNER_NAME}! Apna khayal rakhna. Good night!")
