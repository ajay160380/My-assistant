"""
Reminders Module — Background threaded reminders with sound alerts.
"""
import json
import os
import time
import threading
import datetime
import subprocess

REMINDERS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'reminders.json')
_active_timers = {}
_reminder_callback = None


def set_callback(cb):
    """Set callback function to be called when reminder fires. cb(message)"""
    global _reminder_callback
    _reminder_callback = cb


def _load():
    os.makedirs(os.path.dirname(REMINDERS_PATH), exist_ok=True)
    if os.path.exists(REMINDERS_PATH):
        with open(REMINDERS_PATH, 'r') as f:
            return json.load(f)
    return []


def _save(reminders):
    os.makedirs(os.path.dirname(REMINDERS_PATH), exist_ok=True)
    with open(REMINDERS_PATH, 'w') as f:
        json.dump(reminders, f, indent=2, ensure_ascii=False)


def add_reminder(message, seconds):
    """Add a new reminder that fires after `seconds` seconds."""
    reminders = _load()
    reminder_id = f"rem_{int(time.time())}"
    fire_at = (datetime.datetime.now() + datetime.timedelta(seconds=seconds)).isoformat()
    entry = {
        'id': reminder_id,
        'message': message,
        'fire_at': fire_at,
        'seconds': seconds,
        'status': 'active'
    }
    reminders.append(entry)
    _save(reminders)

    # Start background timer
    def _fire():
        time.sleep(seconds)
        # Play alert sound
        for _ in range(3):
            try:
                subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'], capture_output=True)
                time.sleep(0.5)
            except Exception:
                pass
        # Mark as done
        all_rem = _load()
        for r in all_rem:
            if r['id'] == reminder_id:
                r['status'] = 'done'
                break
        _save(all_rem)
        # Callback
        if _reminder_callback:
            _reminder_callback(f"⏰ Reminder: {message}")
        if reminder_id in _active_timers:
            del _active_timers[reminder_id]

    t = threading.Thread(target=_fire, daemon=True)
    t.start()
    _active_timers[reminder_id] = t
    return entry


def get_reminders(include_done=False):
    """Get all reminders."""
    reminders = _load()
    if not include_done:
        return [r for r in reminders if r['status'] == 'active']
    return reminders


def cancel_reminder(reminder_id):
    """Cancel an active reminder (note: cannot stop sleeping thread, but marks it)."""
    reminders = _load()
    for r in reminders:
        if r['id'] == reminder_id:
            r['status'] = 'cancelled'
            break
    _save(reminders)
    return True


def clear_done():
    """Clear all done/cancelled reminders."""
    reminders = _load()
    reminders = [r for r in reminders if r['status'] == 'active']
    _save(reminders)
