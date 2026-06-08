"""
J.A.R.V.I.S Ultra — Flask Backend
All API routes, Socket events, System Monitoring
"""
import os
import sys
import re
import json
import socket
import subprocess
import threading
import time
import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import webview

# Import core Jarvis engine
import jarvis

# Import models
from models import history, reminders, notes

# ═══ Flask Setup ═══
app = Flask(__name__)
app.config['SECRET_KEY'] = 'jarvis-ultra-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Settings file
SETTINGS_PATH = os.path.join(os.path.dirname(__file__), 'data', 'settings.json')


def load_settings():
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, 'r') as f:
            return json.load(f)
    return {
        'voice': 'hi-IN-MadhurNeural',
        'language': 'hi-IN',
        'owner': jarvis.OWNER_NAME,
        'sensitivity': 300
    }


def save_settings_to_file(settings):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=2)


# ═══ UI Event Handler — Bridge between Jarvis voice engine and Web UI ═══
def ui_event_handler(event_name, data):
    socketio.emit(event_name, data)


# ═══ Routes ═══
@app.route('/')
def index():
    return render_template('index.html',
                           owner=jarvis.OWNER_NAME,
                           assistant=jarvis.ASSISTANT_NAME)


# ═══ API: System Stats ═══
@app.route('/api/system_stats')
def api_system_stats():
    stats = {}
    try:
        # CPU
        result = subprocess.run(['sysctl', '-n', 'hw.model'], capture_output=True, text=True)
        cpu_name = result.stdout.strip()
        # CPU usage via top
        result = subprocess.run(['top', '-l', '1', '-n', '0'], capture_output=True, text=True, timeout=10)
        cpu_match = re.search(r'CPU usage:\s+([\d.]+)%\s+user,\s+([\d.]+)%\s+sys', result.stdout)
        cpu_percent = round(float(cpu_match.group(1)) + float(cpu_match.group(2))) if cpu_match else 0
        stats['cpu_percent'] = min(cpu_percent, 100)
        stats['cpu_name'] = cpu_name

        # RAM
        result = subprocess.run(['vm_stat'], capture_output=True, text=True)
        pages_free = pages_active = pages_speculative = pages_wired = 0
        for line in result.stdout.split('\n'):
            if 'Pages free' in line:
                m = re.search(r'(\d+)', line)
                if m: pages_free = int(m.group(1))
            if 'Pages active' in line:
                m = re.search(r'(\d+)', line)
                if m: pages_active = int(m.group(1))
            if 'Pages speculative' in line:
                m = re.search(r'(\d+)', line)
                if m: pages_speculative = int(m.group(1))
            if 'Pages wired' in line:
                m = re.search(r'(\d+)', line)
                if m: pages_wired = int(m.group(1))

        page_size = 16384
        result2 = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True)
        total_bytes = int(result2.stdout.strip())
        total_gb = round(total_bytes / (1024**3), 1)
        used_pages = pages_active + pages_wired
        used_gb = round((used_pages * page_size) / (1024**3), 1)
        ram_percent = round((used_gb / total_gb) * 100) if total_gb > 0 else 0
        stats['ram_percent'] = min(ram_percent, 100)
        stats['ram_used'] = str(used_gb)
        stats['ram_total'] = str(total_gb)

        # Battery
        result = subprocess.run(['pmset', '-g', 'batt'], capture_output=True, text=True)
        bat_match = re.search(r'(\d+)%', result.stdout)
        bat_pct = int(bat_match.group(1)) if bat_match else 0
        charging = "charging" in result.stdout.lower() and "not charging" not in result.stdout.lower()
        stats['battery_percent'] = bat_pct
        stats['battery_status'] = 'Charging' if charging else 'On Battery'

        # Disk
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            stats['disk_total'] = parts[1]
            stats['disk_used'] = parts[2]
            pct_str = parts[4].replace('%', '')
            stats['disk_percent'] = int(pct_str)
        else:
            stats['disk_total'] = stats['disk_used'] = '?'
            stats['disk_percent'] = 0

        # Local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            stats['local_ip'] = s.getsockname()[0]
            s.close()
        except Exception:
            stats['local_ip'] = 'Unknown'

        # Uptime
        result = subprocess.run(['uptime'], capture_output=True, text=True)
        stats['uptime'] = result.stdout.strip()[:60]

        # Active Apps
        result = subprocess.run(['osascript', '-e',
            'tell application "System Events" to set appNames to name of every process whose background only is false\n'
            'set AppleScript\'s text item delimiters to ", "\nreturn appNames as text'],
            capture_output=True, text=True, timeout=5)
        apps = result.stdout.strip()
        stats['active_apps'] = apps[:200] if apps else 'N/A'

    except Exception as e:
        stats['error'] = str(e)

    return jsonify(stats)


# ═══ API: Weather ═══
@app.route('/api/weather')
def api_weather():
    try:
        result = subprocess.run(
            ['curl', '-s', 'wttr.in/?format=%t|%C'],
            capture_output=True, text=True, timeout=5
        )
        parts = result.stdout.strip().split('|')
        temp = parts[0].strip() if parts else '--'
        desc = parts[1].strip() if len(parts) > 1 else 'Unknown'
        return jsonify({'temp': temp, 'description': desc})
    except Exception:
        return jsonify({'temp': '--', 'description': 'Offline'})


# ═══ API: Command History ═══
@app.route('/api/history')
def api_history():
    q = request.args.get('q', None)
    items = history.get_history(limit=50, search_query=q)
    return jsonify(items)


@app.route('/api/stats')
def api_stats():
    return jsonify(history.get_stats())


# ═══ API: Notes ═══
@app.route('/api/notes', methods=['GET'])
def api_get_notes():
    return jsonify(notes.get_notes())


@app.route('/api/notes', methods=['POST'])
def api_add_note():
    data = request.get_json()
    note = notes.add_note(data.get('content', ''))
    return jsonify(note)


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def api_delete_note(note_id):
    notes.delete_note(note_id)
    return jsonify({'ok': True})


# ═══ API: Settings ═══
@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    return jsonify(load_settings())


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    data = request.get_json()
    save_settings_to_file(data)
    # Apply voice setting to Jarvis
    if 'voice' in data:
        jarvis.TTS_VOICE = data['voice']
    return jsonify({'ok': True})


# ═══ Socket Events ═══
@socketio.on('connect')
def handle_connect():
    socketio.emit('status', 'Standby')


@socketio.on('ui_command')
def handle_ui_command(data):
    action = data.get('action')
    value = data.get('value', 'none')

    def run_cmd():
        success, msg = jarvis.execute_system_command(action, value)
        # Save to history
        history.save_command(
            user_input=f"[UI Button] {action}",
            action='system_cmd', target=action, value=value, success=success
        )
        if msg:
            jarvis.speak(msg)

    threading.Thread(target=run_cmd, daemon=True).start()


@socketio.on('ui_launch_app')
def handle_launch_app(data):
    app_name = data.get('app_name')

    def run_launch():
        success = jarvis.open_application(app_name)
        history.save_command(
            user_input=f"[UI Button] Open {app_name}",
            action='open_app', target=app_name, success=success
        )
        if success:
            jarvis.speak(f"{app_name} khol diya")
        else:
            jarvis.speak(f"Sorry, {app_name} nahi khul paaya")

    threading.Thread(target=run_launch, daemon=True).start()


# ═══ Startup ═══
def start_flask():
    socketio.run(app, port=5000, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)


def start_jarvis():
    time.sleep(2)
    jarvis.set_ui_callback(ui_event_handler)

    # Set reminder callback
    def reminder_fire(msg):
        jarvis.speak(msg)

    reminders.set_callback(reminder_fire)

    # Monkey-patch parse_command to save history
    original_parse = jarvis.parse_command

    def parse_with_history(text):
        result = original_parse(text)
        if result:
            history.save_command(
                user_input=text,
                action=result.get('action', 'unknown'),
                target=result.get('target', ''),
                value=result.get('value', ''),
                success=True
            )
        return result

    jarvis.parse_command = parse_with_history
    jarvis.main()


if __name__ == '__main__':
    # Start Flask
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Start Jarvis Voice Engine
    jarvis_thread = threading.Thread(target=start_jarvis, daemon=True)
    jarvis_thread.start()

    # Start Native Window
    webview.create_window(
        'J.A.R.V.I.S — AI Assistant',
        'http://127.0.0.1:5000',
        width=1200,
        height=800,
        frameless=False,
        background_color='#080c18'
    )
    webview.start()
