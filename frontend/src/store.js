// store.js — the app's only mutable session state, plus localStorage sync.
// Anything the rail or a view needs to react to (login, admin, room membership)
// goes through here instead of being read directly off localStorage in five places.

const listeners = new Set();

function load(key) {
    try {
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

export const state = {
    currentPlayer: load('currentPlayer'),
    adminToken: localStorage.getItem('adminToken'),
    isAdmin: false,
    currentRoomCode: localStorage.getItem('currentRoomCode'),
};

export function subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
}

function notify() {
    for (const fn of listeners) fn(state);
}

export function setPlayer(player) {
    state.currentPlayer = player;
    if (player) {
        localStorage.setItem('currentPlayer', JSON.stringify(player));
    } else {
        localStorage.removeItem('currentPlayer');
    }
    notify();
}

export function setRoomCode(code) {
    state.currentRoomCode = code;
    if (code) {
        localStorage.setItem('currentRoomCode', code);
    } else {
        localStorage.removeItem('currentRoomCode');
    }
    notify();
}

export function setAdmin(token, isAdmin) {
    state.adminToken = token;
    state.isAdmin = isAdmin;
    if (token) {
        localStorage.setItem('adminToken', token);
    } else {
        localStorage.removeItem('adminToken');
    }
    notify();
}

export function logoutPlayer() {
    setPlayer(null);
    setRoomCode(null);
}

export function touch() {
    notify();
}
