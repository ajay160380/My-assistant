"""
Notes Module — JSON-based persistent notes with timestamps and search.
"""
import json
import os
import datetime

NOTES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'notes.json')


def _load():
    os.makedirs(os.path.dirname(NOTES_PATH), exist_ok=True)
    if os.path.exists(NOTES_PATH):
        with open(NOTES_PATH, 'r') as f:
            return json.load(f)
    return []


def _save(notes):
    os.makedirs(os.path.dirname(NOTES_PATH), exist_ok=True)
    with open(NOTES_PATH, 'w') as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def add_note(content):
    """Add a new note."""
    notes = _load()
    note = {
        'id': len(notes) + 1,
        'content': content,
        'created_at': datetime.datetime.now().isoformat(),
        'pinned': False
    }
    notes.append(note)
    _save(notes)
    return note


def get_notes(limit=20, search_query=None):
    """Get notes, optionally filtered."""
    notes = _load()
    if search_query:
        notes = [n for n in notes if search_query.lower() in n['content'].lower()]
    # Sort: pinned first, then by date
    notes.sort(key=lambda x: (not x.get('pinned', False), x.get('created_at', '')), reverse=True)
    return notes[:limit]


def delete_note(note_id):
    """Delete a note by ID."""
    notes = _load()
    notes = [n for n in notes if n['id'] != note_id]
    _save(notes)
    return True


def pin_note(note_id):
    """Toggle pin status of a note."""
    notes = _load()
    for n in notes:
        if n['id'] == note_id:
            n['pinned'] = not n.get('pinned', False)
            break
    _save(notes)
    return True
