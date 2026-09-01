// socket.js — WebSocket connections owned by the app shell, not by a view.
// Previously each game page opened its own socket and threw it away on
// navigation. Now the lobby socket lives for the whole session and the game
// socket survives route swaps within the same game, which is also what a
// future reconnect-with-replay (roadmap Phase 6) needs to build on.

// Always go through the page's own origin: the Vite dev server proxies /api
// with ws:true, and nginx does the same in production.
function wsUrl(path) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}/api${path}`;
}

const statusListeners = new Set();
export const status = { lobby: 'connecting', game: 'idle' };

function setStatus(key, value) {
    status[key] = value;
    for (const fn of statusListeners) fn(status);
}

export function onStatusChange(fn) {
    statusListeners.add(fn);
    return () => statusListeners.delete(fn);
}

// ---------------- Lobby socket (connects once, lives for the session) ----------------

const lobbyListeners = new Set();
let lobbySocket = null;

export function onLobby(fn) {
    lobbyListeners.add(fn);
    return () => lobbyListeners.delete(fn);
}

export function connectLobby() {
    if (lobbySocket && (lobbySocket.readyState === WebSocket.OPEN || lobbySocket.readyState === WebSocket.CONNECTING)) {
        return;
    }
    setStatus('lobby', 'connecting');
    const ws = new WebSocket(wsUrl('/ws/lobby'));
    lobbySocket = ws;

    ws.onopen = () => setStatus('lobby', 'live');
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            for (const fn of lobbyListeners) fn(data);
        } catch (e) {
            console.error('Lobby websocket parse error:', e);
        }
    };
    ws.onclose = () => {
        setStatus('lobby', 'reconnecting');
        setTimeout(connectLobby, 3000);
    };
    ws.onerror = () => ws.close();
}

// ---------------- Game socket (tied to whichever game is active) ----------------

const gameListeners = new Set();
let gameSocket = null;
let gameSocketId = null;

export function onGame(fn) {
    gameListeners.add(fn);
    return () => gameListeners.delete(fn);
}

export function connectGame(gameId) {
    if (gameSocketId === gameId && gameSocket && (gameSocket.readyState === WebSocket.OPEN || gameSocket.readyState === WebSocket.CONNECTING)) {
        return; // already connected to this game
    }
    disconnectGame();
    gameSocketId = gameId;
    setStatus('game', 'connecting');

    const ws = new WebSocket(wsUrl(`/ws/game/${gameId}`));
    gameSocket = ws;

    ws.onopen = () => setStatus('game', 'live');
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            for (const fn of gameListeners) fn(data);
        } catch (e) {
            console.error('Game websocket parse error:', e);
        }
    };
    ws.onclose = () => {
        if (gameSocketId !== gameId) return; // superseded by a newer connectGame() call
        setStatus('game', 'reconnecting');
        setTimeout(() => {
            if (gameSocketId === gameId) connectGame(gameId);
        }, 3000);
    };
    ws.onerror = () => ws.close();
}

export function disconnectGame() {
    gameSocketId = null;
    if (gameSocket) {
        gameSocket.onclose = null;
        gameSocket.close();
        gameSocket = null;
    }
    setStatus('game', 'idle');
}
