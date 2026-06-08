/* ═══════════════════════════════════════════════════════════
   J.A.R.V.I.S Ultra — Frontend JavaScript
   WebSocket, Tabs, Visualizer, System Stats, Toasts
   ═══════════════════════════════════════════════════════════ */

const socket = io();

// ═══ TAB NAVIGATION ═══
const navButtons = document.querySelectorAll('.nav-btn');
const tabContents = document.querySelectorAll('.tab-content');

navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.dataset.tab;
        navButtons.forEach(b => b.classList.remove('active'));
        tabContents.forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + tabName).classList.add('active');

        // Load data on tab switch
        if (tabName === 'system') fetchSystemStats();
        if (tabName === 'history') fetchHistory();
    });
});

// ═══ CLOCK ═══
function updateClock() {
    const now = new Date();
    let h = now.getHours(), m = now.getMinutes();
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    m = m < 10 ? '0' + m : m;
    const timeStr = h + ':' + m + ' ' + ampm;
    document.getElementById('sidebar-clock').innerText = timeStr;
}
setInterval(updateClock, 1000);
updateClock();

// ═══ TOAST NOTIFICATIONS ═══
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    const icons = { info: 'fa-circle-info', success: 'fa-circle-check', error: 'fa-circle-xmark' };
    toast.innerHTML = '<i class="fa-solid ' + (icons[type] || icons.info) + '"></i><span>' + message + '</span>';
    container.appendChild(toast);
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 4000);
}

// ═══ SOCKET EVENTS ═══
socket.on('status', function(data) {
    const statusText = document.getElementById('sidebar-status-text');
    const statusDot = document.getElementById('sidebar-status-dot');
    const visDot = document.getElementById('vis-dot');
    const visText = document.getElementById('vis-status-text');

    statusText.innerText = data;
    visText.innerText = data;

    statusDot.className = 'status-dot';
    if (data.toLowerCase().includes('listening')) {
        statusDot.classList.add('listening');
    } else if (data.toLowerCase().includes('processing')) {
        statusDot.classList.add('processing');
    } else if (data.toLowerCase().includes('speaking')) {
        statusDot.classList.add('speaking');
        startVisualizerAnimation();
    }

    if (!data.toLowerCase().includes('speaking')) {
        stopVisualizerAnimation();
    }
});

socket.on('chat_message', function(data) {
    addChatMessage(data.sender, data.text);
    // Show toast for Jarvis replies
    if (data.sender === 'Jarvis') {
        showToast(data.text.substring(0, 80) + (data.text.length > 80 ? '...' : ''), 'success');
    }
});

socket.on('toast', function(data) {
    showToast(data.message, data.type || 'info');
});

// ═══ CHAT ═══
function addChatMessage(sender, text) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    if (sender === 'Jarvis') msgDiv.className = 'chat-msg jarvis';
    else if (sender === 'System') msgDiv.className = 'chat-msg system';
    else msgDiv.className = 'chat-msg user';

    const bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerText = text;
    msgDiv.appendChild(bubble);
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

function clearChat() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '<div class="chat-msg system"><div class="msg-bubble">Chat cleared.</div></div>';
}

// ═══ QUICK ACTIONS & APP LAUNCHER ═══
function sendCmd(action) {
    socket.emit('ui_command', { action: action });
    showToast('Executing: ' + action, 'info');
}

function launchApp(appName) {
    socket.emit('ui_launch_app', { app_name: appName });
    showToast('Opening ' + appName + '...', 'info');
}

// ═══ NOTES ═══
function addNote() {
    const input = document.getElementById('note-input');
    const text = input.value.trim();
    if (!text) return;
    fetch('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text })
    }).then(r => r.json()).then(() => {
        input.value = '';
        loadNotes();
        showToast('Note saved!', 'success');
    });
}

function deleteNote(noteId) {
    fetch('/api/notes/' + noteId, { method: 'DELETE' })
        .then(r => r.json()).then(() => loadNotes());
}

function loadNotes() {
    fetch('/api/notes').then(r => r.json()).then(notes => {
        const list = document.getElementById('notes-list');
        if (!notes.length) {
            list.innerHTML = '<p class="empty-state">No notes yet</p>';
            return;
        }
        list.innerHTML = notes.map(n => {
            const t = new Date(n.created_at);
            const timeStr = t.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
            return '<div class="note-item">' +
                '<span class="note-text">' + escapeHtml(n.content) + '</span>' +
                '<span class="note-time">' + timeStr + '</span>' +
                '<button class="note-del" onclick="deleteNote(' + n.id + ')"><i class="fa-solid fa-xmark"></i></button>' +
                '</div>';
        }).join('');
    });
}

// Enter key for notes input
document.getElementById('note-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') addNote();
});

// ═══ SYSTEM STATS ═══
function fetchSystemStats() {
    fetch('/api/system_stats').then(r => r.json()).then(data => {
        updateRing('ring-cpu', data.cpu_percent, 'cpu-value', data.cpu_percent + '%');
        document.getElementById('cpu-detail').innerText = data.cpu_name || 'Apple Silicon';

        updateRing('ring-ram', data.ram_percent, 'ram-value', data.ram_percent + '%');
        document.getElementById('ram-detail').innerText = data.ram_used + ' / ' + data.ram_total + ' GB';

        updateRing('ring-battery', data.battery_percent, 'battery-value', data.battery_percent + '%');
        document.getElementById('battery-detail').innerText = data.battery_status;
        document.getElementById('stat-battery').innerText = data.battery_percent + '%';

        updateRing('ring-disk', data.disk_percent, 'disk-value', data.disk_percent + '%');
        document.getElementById('disk-detail').innerText = data.disk_used + ' / ' + data.disk_total;

        document.getElementById('network-info').innerText = 'IP: ' + data.local_ip;
        document.getElementById('uptime-info').innerText = data.uptime;
        document.getElementById('active-apps-info').innerText = data.active_apps;
    }).catch(() => {});
}

function updateRing(ringId, percent, valueId, valueText) {
    const circumference = 2 * Math.PI * 52; // r=52
    const offset = circumference - (percent / 100) * circumference;
    document.getElementById(ringId).style.strokeDashoffset = offset;
    document.getElementById(valueId).innerText = valueText;
}

// ═══ HISTORY ═══
function fetchHistory(query) {
    let url = '/api/history';
    if (query) url += '?q=' + encodeURIComponent(query);
    fetch(url).then(r => r.json()).then(items => {
        const list = document.getElementById('history-list');
        if (!items.length) {
            list.innerHTML = '<p class="empty-state">No commands found.</p>';
            return;
        }
        list.innerHTML = items.map(item => {
            const t = new Date(item.timestamp);
            const timeStr = t.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) + ' ' +
                            t.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
            const actionIcons = {
                open_app: 'fa-window-maximize', close_app: 'fa-xmark', web_search: 'fa-globe',
                youtube: 'fa-youtube', system_cmd: 'fa-laptop', chat: 'fa-comments',
                play_music: 'fa-music', send_message: 'fa-envelope', run_shell: 'fa-terminal',
            };
            const icon = actionIcons[item.action] || 'fa-microphone';
            return '<div class="history-item">' +
                '<div class="history-icon"><i class="fa-solid ' + icon + '"></i></div>' +
                '<div class="history-info">' +
                '<div class="h-cmd">' + escapeHtml(item.user_input) + '</div>' +
                '<div class="h-action">' + (item.action || 'unknown') + (item.target ? ' → ' + item.target : '') + '</div>' +
                '</div>' +
                '<span class="history-time">' + timeStr + '</span>' +
                '</div>';
        }).join('');
    });
}

document.getElementById('history-search-input').addEventListener('input', function() {
    fetchHistory(this.value);
});

// ═══ WEATHER ═══
function fetchWeather() {
    fetch('/api/weather').then(r => r.json()).then(data => {
        document.getElementById('stat-weather').innerText = data.temp;
        document.getElementById('stat-weather-desc').innerText = data.description;
    }).catch(() => {
        document.getElementById('stat-weather').innerText = '--';
        document.getElementById('stat-weather-desc').innerText = 'Offline';
    });
}

// ═══ STATS ═══
function fetchCommandStats() {
    fetch('/api/stats').then(r => r.json()).then(data => {
        document.getElementById('stat-total-cmds').innerText = data.total_commands;
        document.getElementById('stat-today-cmds').innerText = data.today_commands;
    }).catch(() => {});
}

// ═══ SETTINGS ═══
function setAccent(color, el) {
    document.documentElement.style.setProperty('--accent', color);
    // Calculate RGB
    const r = parseInt(color.slice(1,3), 16);
    const g = parseInt(color.slice(3,5), 16);
    const b = parseInt(color.slice(5,7), 16);
    document.documentElement.style.setProperty('--accent-rgb', r + ', ' + g + ', ' + b);
    document.documentElement.style.setProperty('--accent-glow', 'rgba(' + r + ', ' + g + ', ' + b + ', 0.4)');
    document.documentElement.style.setProperty('--accent-soft', 'rgba(' + r + ', ' + g + ', ' + b + ', 0.12)');
    document.querySelectorAll('.color-dot').forEach(d => d.classList.remove('active'));
    el.classList.add('active');
}

function saveSettings() {
    const settings = {
        voice: document.getElementById('setting-voice').value,
        language: document.getElementById('setting-language').value,
        owner: document.getElementById('setting-owner').value,
        sensitivity: document.getElementById('setting-sensitivity').value,
    };
    fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    }).then(r => r.json()).then(() => {
        showToast('Settings saved!', 'success');
    });
}

// ═══ CANVAS VISUALIZER ═══
const canvas = document.getElementById('visualizer-canvas');
const ctx = canvas.getContext('2d');
let animationId = null;
let isAnimating = false;

function drawIdleVisualizer() {
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const bars = 40;
    const barW = w / bars - 2;
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#3b82f6';

    for (let i = 0; i < bars; i++) {
        const barH = 4 + Math.sin(Date.now() * 0.002 + i * 0.3) * 3;
        const x = i * (barW + 2);
        const y = (h - barH) / 2;
        ctx.fillStyle = accent + '40';
        ctx.beginPath();
        ctx.roundRect(x, y, barW, barH, 2);
        ctx.fill();
    }
    animationId = requestAnimationFrame(drawIdleVisualizer);
}

function drawActiveVisualizer() {
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const bars = 40;
    const barW = w / bars - 2;
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#3b82f6';

    for (let i = 0; i < bars; i++) {
        const barH = 10 + Math.random() * (h * 0.7) * Math.sin(Date.now() * 0.005 + i * 0.5) ** 2;
        const x = i * (barW + 2);
        const y = (h - barH) / 2;

        const gradient = ctx.createLinearGradient(x, y, x, y + barH);
        gradient.addColorStop(0, accent + 'cc');
        gradient.addColorStop(0.5, accent);
        gradient.addColorStop(1, accent + 'cc');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barW, barH, 3);
        ctx.fill();
    }
    if (isAnimating) animationId = requestAnimationFrame(drawActiveVisualizer);
}

function startVisualizerAnimation() {
    isAnimating = true;
    if (animationId) cancelAnimationFrame(animationId);
    drawActiveVisualizer();
}

function stopVisualizerAnimation() {
    isAnimating = false;
    if (animationId) cancelAnimationFrame(animationId);
    drawIdleVisualizer();
}

// ═══ UTILITY ═══
function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}

// ═══ INITIALIZATION ═══
document.addEventListener('DOMContentLoaded', function() {
    drawIdleVisualizer();
    loadNotes();
    fetchWeather();
    fetchCommandStats();
    // Auto-refresh system stats every 10s when on system tab
    setInterval(() => {
        if (document.getElementById('tab-system').classList.contains('active')) {
            fetchSystemStats();
        }
        fetchCommandStats();
    }, 10000);
});
