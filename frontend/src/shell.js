// shell.js — the persistent chrome: rail (nav + connection status + player
// badge), the admin login modal, and toast notifications. Rendered once by
// main.js and never torn down between route changes.

import { apiCall, escapeHTML, ROOT_URL } from './api.js';
import { state, subscribe, setAdmin, setRoomCode, logoutPlayer as storeLogoutPlayer } from './store.js';
import { status as socketStatus, onStatusChange } from './socket.js';
import { navigate } from './router.js';

const NAV_ITEMS = [
    { path: '/', label: 'GAMES' },
    { path: '/market', label: 'MARKET' },
    { path: '/two-thirds', label: '2/3 AVERAGE' },
    { path: '/fish-pond', label: 'FISH POND' },
    { path: '/horse-race', label: 'HORSE RACE' },
];

export function renderShell(root) {
    root.innerHTML = `
      <div class="rail" id="rail"></div>

      <div class="modal" id="adminModal">
        <div class="modal-content">
          <button class="modal-close" id="adminModalClose" aria-label="Close">&times;</button>
          <h2>Admin Login</h2>
          <form id="adminLoginForm">
            <div>
              <label for="adminUsername">Username</label>
              <input type="text" id="adminUsername" required autocomplete="username" />
            </div>
            <div>
              <label for="adminPassword">Password</label>
              <input type="password" id="adminPassword" required autocomplete="current-password" />
            </div>
            <button type="submit" class="btn-primary btn-block">Log in</button>
          </form>
          <div id="adminLoginError" class="state-msg error mt-16" style="display:none"></div>
        </div>
      </div>

      <main class="app-container" id="view"></main>

      <div id="notification" class="notification"></div>
    `;

    renderRail();
    subscribe(renderRail);
    onStatusChange(renderRail);

    document.getElementById('adminModalClose').addEventListener('click', closeAdminLogin);
    document.getElementById('adminModal').addEventListener('click', (e) => {
        if (e.target.id === 'adminModal') closeAdminLogin();
    });
    document.getElementById('adminLoginForm').addEventListener('submit', handleAdminLogin);

    checkAdminStatus();
}

function statusWord(s) {
    if (s === 'live') return { label: 'live', cls: 'buy' };
    if (s === 'connecting') return { label: 'connecting', cls: 'think' };
    return { label: 'offline', cls: 'dim' };
}

function renderRail() {
    const rail = document.getElementById('rail');
    if (!rail) return;

    const path = window.location.pathname;
    const { label, cls } = statusWord(socketStatus.lobby);

    const navHtml = NAV_ITEMS.map(item => {
        const on = item.path === '/' ? path === '/' : path.startsWith(item.path);
        return `<a href="${item.path}" class="${on ? 'on' : ''}">${item.label}</a>`;
    }).join('');

    let sysHtml = `<span><i class="dot ${cls}"></i>${label}${cls === 'buy' ? '<span class="cursor"></span>' : ''}</span>`;
    if (state.currentPlayer) {
        sysHtml += `<span>${escapeHTML(state.currentPlayer.name)}</span>`;
        sysHtml += `<button id="railLogout">log out</button>`;
    }
    if (state.isAdmin) {
        sysHtml += `<span class="amber">admin</span>`;
        sysHtml += `<button id="railAdminLogout">log out</button>`;
    } else {
        sysHtml += `<button id="railAdminLogin">admin</button>`;
    }

    rail.innerHTML = `
      <a href="/" class="rail-brand"><i class="${cls === 'buy' ? 'live' : ''}"></i>THINK TWICE</a>
      <nav class="rail-nav">${navHtml}</nav>
      <div class="rail-sys">${sysHtml}</div>
    `;

    document.getElementById('railLogout')?.addEventListener('click', () => {
        storeLogoutPlayer();
        navigate('/');
    });
    document.getElementById('railAdminLogin')?.addEventListener('click', showAdminLogin);
    document.getElementById('railAdminLogout')?.addEventListener('click', () => {
        setAdmin(null, false);
        showNotification('Logged out of admin', 'info');
    });
}

// ---------------- Admin login modal ----------------

function showAdminLogin() {
    document.getElementById('adminModal').classList.add('show');
    document.getElementById('adminLoginError').style.display = 'none';
}

function closeAdminLogin() {
    document.getElementById('adminModal').classList.remove('show');
    document.getElementById('adminUsername').value = '';
    document.getElementById('adminPassword').value = '';
}

async function handleAdminLogin(e) {
    e.preventDefault();
    const username = document.getElementById('adminUsername').value;
    const password = document.getElementById('adminPassword').value;

    try {
        const response = await fetch(`${ROOT_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        if (!response.ok) throw new Error('Invalid credentials');
        const data = await response.json();
        setAdmin(data.access_token, true);
        closeAdminLogin();
        showNotification('Admin login successful', 'success');
    } catch (error) {
        const errorEl = document.getElementById('adminLoginError');
        errorEl.textContent = error.message;
        errorEl.style.display = 'block';
    }
}

async function checkAdminStatus() {
    if (!state.adminToken) return;
    try {
        const response = await fetch(`${ROOT_URL}/api/auth/verify`, {
            headers: { Authorization: `Bearer ${state.adminToken}` },
        });
        setAdmin(state.adminToken, response.ok);
    } catch {
        setAdmin(null, false);
    }
}

// ---------------- Notifications ----------------

let notifyTimer = null;

export function showNotification(message, type = 'info') {
    const el = document.getElementById('notification');
    if (!el) {
        console.log('Notification:', message);
        return;
    }
    el.textContent = message;
    el.className = `notification ${type} show`;
    clearTimeout(notifyTimer);
    notifyTimer = setTimeout(() => el.classList.remove('show'), 3000);
}

/** Player-facing "leave active game" confirmation + API call, shared by every game view. */
export async function leaveActiveGame(isHost) {
    const confirmMsg = isHost
        ? 'You are the Host. Leaving will transfer host privileges or close the room. Continue?'
        : 'Leave this game?';
    if (!confirm(confirmMsg)) return false;

    if (state.currentRoomCode && state.currentPlayer) {
        try {
            await apiCall(`/rooms/${state.currentRoomCode}/leave?player_id=${state.currentPlayer.id}`, 'POST');
        } catch (e) {
            console.error('Error leaving room:', e);
        }
    }
    setRoomCode(null);
    return true;
}
