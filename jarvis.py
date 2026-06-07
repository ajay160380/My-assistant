#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║   J.A.R.V.I.S — Just A Rather Very Intelligent System          ║
║   Advanced Personal AI Voice Assistant for macOS                ║
║   Owner: Ajay Vishwakarma                                       ║
║   Version: 3.0 — Ultimate Edition                               ║
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
import speech_recognition as sr
from groq import Groq

# ━━━━━━━━━━━━━━━━━━━━━━ CONFIGURATION ━━━━━━━━━━━━━━━━━━━━━━
OWNER_NAME = "Ajay"
ASSISTANT_NAME = "Jarvis"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY environment variable not set!")
    print("   Run: export GROQ_API_KEY='your-api-key-here'")
    sys.exit(1)
TTS_VOICE = "Rishi"  # Apple's premium Indian English male voice (Siri-quality neural TTS)
LISTEN_TIMEOUT = 8
PHRASE_LIMIT = 15
MAX_MEMORY = 12

# ━━━━━━━━━━━━━━━━━━━━━━ INITIALIZATION ━━━━━━━━━━━━━━━━━━━━━━
client = Groq(api_key=GROQ_API_KEY)
conversation_memory = []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    TEXT-TO-SPEECH (macOS Native — Siri Quality)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def speak(text):
    """Speak text using macOS native TTS — Siri-quality, instant, no internet needed for TTS."""
    if not text or str(text).strip().lower() in ("none", ""):
        return
    print(f"\n  🔊 {ASSISTANT_NAME}: {text}", flush=True)
    try:
        # Use macOS 'say' command with premium neural voice
        subprocess.run(['say', '-v', TTS_VOICE, '-r', '190', text], check=True)
    except Exception as e:
        print(f"  ⚠️  TTS error: {e}")


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
    # Check if the text starts with or contains a wake word
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
        # Use macOS built-in sound for activation feedback
        subprocess.run(['afplay', '/System/Library/Sounds/Tink.aiff'], check=True,
                       capture_output=True, timeout=2)
    except Exception:
        pass  # Silently ignore if sound can't play


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    SPEECH RECOGNITION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def passive_listen(recognizer, source):
    """Passively listen for the wake word. Returns remaining command text or empty string."""
    try:
        audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=5)
        text = recognizer.recognize_google(audio, language='hi-IN')
        detected, remaining = contains_wake_word(text)
        if detected:
            print(f"\n  ✨ Wake word detected! (heard: \"{text}\")", flush=True)
            return True, remaining
        return False, ""
    except sr.WaitTimeoutError:
        return False, ""
    except sr.UnknownValueError:
        return False, ""
    except sr.RequestError as e:
        print(f"  ⚠️  Speech API error: {e}")
        return False, ""
    except Exception:
        return False, ""


def active_listen(recognizer, source):
    """Actively listen for a command after wake word. Returns transcribed text or None."""
    print("  🎤 Listening for command...", flush=True)
    try:
        audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=PHRASE_LIMIT)
        print("  ⏳ Processing...", flush=True)
        text = recognizer.recognize_google(audio, language='hi-IN')
        print(f"  👤 You: {text}", flush=True)
        return text
    except sr.WaitTimeoutError:
        print("  ⏱️  Timeout — no command heard.", flush=True)
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
        f'1. "open_app" — Open a macOS app. Target = exact English name (Safari, Spotify, WhatsApp, Notes, etc.)\n'
        f'2. "web_search" — Google search. Target = search query (translate to English for better results).\n'
        f'3. "youtube" — Play/search on YouTube. Target = what to search/play.\n'
        f'4. "send_message" — Send message. Target = contact name. Value = message text. Platform = "whatsapp" or "imessage".\n'
        f'5. "play_music" — Play music on Spotify. Target = song/artist name.\n'
        f'6. "system_cmd" — System command. Target = one of: screenshot, volume_up, volume_down, volume_mute, battery, lock_screen, sleep.\n'
        f'7. "chat" — Conversation, greetings, jokes, questions, time/date queries, compliments, etc.\n'
        f"   Target = \"none\". Value = your warm, natural reply.\n"
        f"   For chat replies: Be DETAILED and INTERESTING. Don't just say 'namaste'. Have a real conversation.\n"
        f"   If asked about time, include the exact time. If asked about date, include the full date and day.\n"
        f"   If asked about the owner, you know his name is {OWNER_NAME}.\n"
        f'8. "unknown" — Cannot determine intent. Value = a helpful suggestion.\n\n'
        f"CRITICAL RULES:\n"
        f"- User speaks Hindi, Hinglish, or English. You MUST understand all three perfectly.\n"
        f"- App names must ALWAYS be in English: Safari, WhatsApp, Notes, etc.\n"
        f"- IMPORTANT — LANGUAGE RULE FOR ALL REPLIES (value field):\n"
        f"  Always reply in ROMAN HINGLISH (Hindi written in English/Latin letters).\n"
        f"  NEVER use Devanagari script (नमस्ते, अभी, etc). ALWAYS use Roman: Namaste, Abhi, etc.\n"
        f"  Example: 'Abhi time 11:25 PM hai aur aaj 7 June 2026 hai, Sunday.'\n"
        f"  Example: 'Good morning Ajay! Kaise ho? Bolo kya karna hai.'\n"
        f"- Be warm, human-like, charming. NOT robotic.\n"
        f"- For send_message: Default platform is 'whatsapp' if user mentions WhatsApp, else 'imessage'.\n"
        f"- For youtube: If user says 'YouTube par gaana bajao' or 'YouTube pe search karo', use this action.\n"
        f"- NEVER output anything except the JSON object.\n"
    )


def parse_command(text):
    """Send text to Groq LLM and get structured JSON intent."""
    global conversation_memory

    system_prompt = build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation memory for context
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

        # Clean markdown if LLM wraps in code block
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)

        # Sometimes LLM outputs multiple JSON or extra text — take first valid JSON
        match = re.search(r'\{[^{}]*\}', content)
        if match:
            content = match.group(0)

        parsed = json.loads(content)

        # Save conversation context
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
#                    macOS AUTOMATION FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run_applescript(script):
    """Run an AppleScript command silently."""
    return subprocess.run(['osascript', '-e', script], capture_output=True, text=True)


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


def search_web(query):
    """Open a Google search in the default browser."""
    try:
        encoded = urllib.parse.quote(query)
        subprocess.run(['open', f'https://www.google.com/search?q={encoded}'], check=True)
        return True
    except Exception:
        return False


def search_youtube(query):
    """Search YouTube in the default browser."""
    try:
        encoded = urllib.parse.quote(query)
        subprocess.run(['open', f'https://www.youtube.com/results?search_query={encoded}'], check=True)
        return True
    except Exception:
        return False


def send_imessage(contact, message):
    """Send an iMessage via the Messages app."""
    try:
        run_applescript(f'tell application "Messages" to send "{message}" to buddy "{contact}"')
        return True
    except Exception:
        return False


def clipboard_set(text):
    """Copy text to macOS clipboard."""
    process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
    process.communicate(text.encode('utf-8'))


def send_whatsapp_message(contact, message):
    """Open WhatsApp, search contact, send message using clipboard for Hindi support."""
    safe_msg = message if message and message != "none" else ""
    try:
        # Step 1: Open WhatsApp
        subprocess.run(['open', '-a', 'WhatsApp'], check=True)
        time.sleep(2)

        # Step 2: Escape any previous state
        run_applescript('tell application "System Events" to key code 53')  # Escape
        time.sleep(0.5)

        # Step 3: Open search (Cmd+F)
        run_applescript('tell application "System Events" to keystroke "f" using command down')
        time.sleep(0.8)

        # Step 4: Clear old search text (Cmd+A then Delete)
        run_applescript('tell application "System Events" to keystroke "a" using command down')
        time.sleep(0.2)
        run_applescript('tell application "System Events" to key code 51')  # Delete
        time.sleep(0.3)

        # Step 5: Paste contact name via clipboard (supports Hindi/Unicode)
        clipboard_set(contact)
        run_applescript('tell application "System Events" to keystroke "v" using command down')
        time.sleep(2)

        # Step 6: Select first result (Down arrow + Enter)
        run_applescript('tell application "System Events" to key code 125')  # Down
        time.sleep(0.3)
        run_applescript('tell application "System Events" to key code 36')  # Enter
        time.sleep(1.5)

        # Step 7: Type and send message
        if safe_msg:
            clipboard_set(safe_msg)
            run_applescript('tell application "System Events" to keystroke "v" using command down')
            time.sleep(0.5)
            run_applescript('tell application "System Events" to key code 36')  # Enter to send

        return True
    except Exception as e:
        print(f"  ⚠️  WhatsApp failed: {e}")
        print("  💡 Tip: Go to System Settings → Privacy & Security → Accessibility → Add Terminal")
        return False


def play_music(song_name):
    """Search and play music on Spotify."""
    try:
        subprocess.run(['open', '-a', 'Spotify'], check=True)
        time.sleep(2)
        # Use Spotify search shortcut (Cmd+L focuses search bar)
        run_applescript('tell application "System Events" to tell process "Spotify" to keystroke "l" using command down')
        time.sleep(0.5)
        clipboard_set(song_name)
        run_applescript('tell application "System Events" to keystroke "v" using command down')
        time.sleep(1.5)
        run_applescript('tell application "System Events" to key code 36')  # Enter
        return True
    except Exception:
        return False


def execute_system_command(cmd):
    """Execute macOS system commands."""
    try:
        if cmd == "screenshot":
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.expanduser(f'~/Desktop/screenshot_{ts}.png')
            subprocess.run(['screencapture', '-i', path])
            return True, f"Screenshot saved to Desktop"

        elif cmd == "volume_up":
            run_applescript('set volume output volume ((output volume of (get volume settings)) + 15)')
            return True, "Volume badha diya"

        elif cmd == "volume_down":
            run_applescript('set volume output volume ((output volume of (get volume settings)) - 15)')
            return True, "Volume kam kar diya"

        elif cmd == "volume_mute":
            run_applescript('set volume output muted true')
            return True, "Volume mute kar diya"

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
            subprocess.run(['pmset', 'sleepnow'], capture_output=True)
            return True, "System sleep mode mein ja raha hai"

        else:
            return False, f"Yeh system command samajh nahi aaya: {cmd}"

    except Exception as e:
        return False, f"System command fail: {e}"


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
    print("  🤖 J.A.R.V.I.S — Personal AI Assistant v3.0")
    print(f"  👤 Owner: {OWNER_NAME}")
    print(f"  🕐 {datetime.datetime.now().strftime('%A, %d %B %Y — %I:%M %p')}")
    print(f"  🧠 AI Model: Llama 3.3 70B (Groq)")
    print(f"  🔊 Voice: Apple Siri Neural ({TTS_VOICE})")
    print(f"  🗣️  Wake Word: 'Jarvis' / 'Hi Jarvis' / 'Hey Jarvis'")
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
            # Show a subtle indicator that Jarvis is in standby
            print("  💤 Standby — say 'Jarvis' to wake me up...", end="\r", flush=True)
            detected, remaining_command = passive_listen(recognizer, source)

            if not detected:
                continue  # No wake word — keep waiting silently

            # ━━━━━━━━━━ STAGE 2: WAKE WORD DETECTED — GET COMMAND ━━━━━━━━━━
            play_activation_sound()

            # If user said "Jarvis open Safari" in one go, remaining_command has the command
            if remaining_command and remaining_command.strip():
                text = remaining_command.strip()
                print(f"  👤 You: {text}", flush=True)
            else:
                # User just said "Jarvis" — wait for the follow-up command
                speak("Haan, bolo")
                text = active_listen(recognizer, source)
                if not text:
                    speak("Koi command nahi mili. Main wapas standby pe ja raha hoon.")
                    continue

            # ━━━━━━━━━━ STAGE 3: PARSE & EXECUTE ━━━━━━━━━━
            parsed = parse_command(text)
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

            elif action == "web_search":
                speak(f"Google par search kar raha hoon")
                if not search_web(target):
                    speak("Search mein problem aa gayi")

            elif action == "youtube":
                speak(f"YouTube par dhundh raha hoon {target}")
                if not search_youtube(target):
                    speak("YouTube search mein problem aa gayi")

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
                success, msg = execute_system_command(target)
                speak(msg)

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
