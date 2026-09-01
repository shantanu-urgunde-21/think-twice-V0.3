// views/home.js — registration, the game catalog, room lobby, leaderboard,
// and the admin panel. This is the one view most players land on first.

import { apiCall, escapeHTML } from '../api.js';
import { state, setPlayer, setRoomCode } from '../store.js';
import { onLobby } from '../socket.js';
import { navigate } from '../router.js';
import { showNotification } from '../shell.js';

const GAME_META = {
    market: { label: 'Hidden Market', route: '/market', players: '2–6 players', desc: 'Trade one commodity on a private signal. The price is whatever the room\'s orders make it.', createLabel: true },
    two_thirds: { label: '2/3 of the Average', route: '/two-thirds', players: '2–20 players', desc: 'Guess two-thirds of everyone\'s average guess. Then guess what they guessed you\'d guess.', createLabel: true },
    fish_pond: { label: 'Fish Pond', route: '/fish-pond', players: '2–8 players', desc: 'A shared stock that regenerates each round. Take too much and there\'s nothing left to take.', createLabel: true },
    horse_race: { label: 'Horse Racing', route: '/horse-race', players: 'solo', desc: 'Identify the 3 fastest horses from a field of 25 in as few rounds as possible.', createLabel: false },
};

const GAME_LABELS = Object.fromEntries(Object.entries(GAME_META).map(([k, v]) => [k, v.label]));

export function renderHome(el, params = {}) {
    let disposed = false;
    let room = null;
    let stats = { total_players: 0, max_players: 0, active_games: 0 };
    let leaderboard = [];
    let enabledGames = new Set(Object.keys(GAME_META));
    let allGameSettings = [];
    let pendingJoinCode = params.joinCode || null;

    async function loadAll() {
        const tasks = [
            apiCall('/stats').then(s => { stats = s; }).catch(() => {}),
            apiCall('/leaderboard').then(l => { leaderboard = l; }).catch(() => {}),
            apiCall('/games/enabled').then(list => { enabledGames = new Set(list.map(g => g.game_name)); }).catch(() => {}),
        ];
        if (state.isAdmin) {
            tasks.push(apiCall('/games/settings').then(list => { allGameSettings = list; }).catch(() => {}));
        }
        await Promise.all(tasks);
    }

    async function checkRedirectToActiveGame() {
        if (!state.currentPlayer) return false;
        try {
            const active = await apiCall(`/rooms/active-player-game/${state.currentPlayer.id}`);
            if (active && GAME_META[active.game_name]) {
                setRoomCode(null);
                navigate(GAME_META[active.game_name].route);
                return true;
            }
        } catch {
            // no active game — normal case
        }
        return false;
    }

    async function loadRoom() {
        if (!state.currentRoomCode) { room = null; return; }
        try {
            const r = await apiCall(`/rooms/${state.currentRoomCode}`);
            if (r.status === 'active') {
                setRoomCode(null);
                await checkRedirectToActiveGame();
                room = null;
                return;
            }
            room = r;
        } catch {
            setRoomCode(null);
            room = null;
        }
    }

    async function attemptPendingJoin() {
        if (!pendingJoinCode || !state.currentPlayer || state.currentRoomCode) return;
        const code = pendingJoinCode;
        pendingJoinCode = null;
        try {
            const r = await apiCall('/rooms/join', 'POST', { player_id: state.currentPlayer.id, room_code: code });
            setRoomCode(r.room_code);
            room = r;
            showNotification(`Joined room ${r.room_code}`, 'success');
        } catch (e) {
            showNotification(e.message, 'error');
        }
    }

    async function refresh() {
        if (disposed) return;
        if (await checkRedirectToActiveGame()) return;
        await loadAll();
        await attemptPendingJoin();
        await loadRoom();
        if (!disposed) render();
    }

    function render() {
        if (state.currentPlayer && room) {
            el.innerHTML = renderLobby(room);
            wireLobby();
        } else if (state.currentPlayer) {
            el.innerHTML = renderCatalog();
            wireCatalog();
        } else {
            el.innerHTML = renderRegistration();
            wireRegistration();
        }
    }

    // ---------------- Registration ----------------

    function renderRegistration() {
        const joinNote = pendingJoinCode
            ? `<p class="state-msg warn mt-16">Enter a name to join room <strong class="text-amber">${escapeHTML(pendingJoinCode)}</strong>.</p>`
            : '';
        return `
          <div class="eyebrow">Think Twice</div>
          <h2 style="font-size:23px;margin-bottom:6px;">Four games about what everyone else will do.</h2>
          <p class="lede mt-16">Classic game-theory experiments, playable with friends in a browser. Register a name to play — no email, no password.</p>

          <section class="panel box pad" style="max-width:440px;">
            <h3>Register</h3>
            <form id="registerForm">
              <div>
                <label for="playerName">Name</label>
                <input type="text" id="playerName" placeholder="Your name" required />
              </div>
              <div>
                <label for="playerRegisterPasscode">PIN (optional)</label>
                <input type="text" id="playerRegisterPasscode" placeholder="4-6 digits — auto-generated if blank" maxlength="6" />
              </div>
              <button type="submit" class="btn-primary btn-block">Register</button>
            </form>
            <div id="registeredPin" class="state-msg success mt-16" style="display:none"></div>
            ${joinNote}
          </section>

          <section class="panel box pad" style="max-width:440px;" id="existingPlayerSection" style="display:none">
            <h3>Or log back in</h3>
            <div class="flex-row">
              <select id="existingPlayers" style="flex:1"><option value="">Choose player...</option></select>
            </div>
            <div class="flex-row mt-16">
              <input type="text" id="playerPasscode" placeholder="PIN" style="max-width:120px" />
              <button id="selectPlayerBtn">Log in</button>
            </div>
          </section>
        `;
    }

    function wireRegistration() {
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('playerName').value.trim();
            const passcode = document.getElementById('playerRegisterPasscode').value.trim();
            const payload = { name };
            if (passcode) payload.passcode = passcode;
            try {
                const player = await apiCall('/players', 'POST', payload);
                setPlayer(player);
                const pinBox = document.getElementById('registeredPin');
                pinBox.style.display = 'block';
                pinBox.innerHTML = `Registered. Your PIN is <strong class="text-amber">${escapeHTML(player.passcode)}</strong> — save it to log back in later.`;
                await refresh();
            } catch (error) {
                showNotification(error.message, 'error');
            }
        });

        apiCall('/players').then(players => {
            if (disposed || !players.length) return;
            const section = document.getElementById('existingPlayerSection');
            const select = document.getElementById('existingPlayers');
            players.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                select.appendChild(opt);
            });
            section.style.display = 'block';
        }).catch(() => {});

        document.getElementById('selectPlayerBtn')?.addEventListener('click', async () => {
            const select = document.getElementById('existingPlayers');
            if (!select.value) return;
            const name = select.options[select.selectedIndex].text;
            const passcode = document.getElementById('playerPasscode').value.trim();
            if (!passcode) { showNotification('Enter your PIN', 'error'); return; }
            try {
                const player = await apiCall('/players/verify', 'POST', { name, passcode });
                setPlayer(player);
                await refresh();
            } catch (error) {
                showNotification(error.message, 'error');
            }
        });
    }

    // ---------------- Catalog ----------------

    function renderCatalog() {
        const cards = Object.entries(GAME_META)
            .filter(([name]) => enabledGames.has(name))
            .map(([name, meta]) => `
              <button class="card" data-game="${name}">
                <span class="tag live">${meta.players} · live</span>
                <h4>${meta.label}</h4>
                <p>${meta.desc}</p>
                <span class="go">${meta.createLabel ? 'Create room' : 'Play now'} →</span>
              </button>
            `).join('');

        return `
          <div class="grid-2">
            <div class="box">
              <div class="pad">
                <div class="eyebrow">Welcome back</div>
                <h2>${escapeHTML(state.currentPlayer.name)}</h2>
                <p class="mt-16">PIN <span class="text-mono text-amber">${escapeHTML(state.currentPlayer.passcode)}</span> — needed to log back in on another device.</p>
              </div>
              <div class="rule-top pad">
                <h3>Games</h3>
                <div class="cards mt-16">${cards || '<p>No games are enabled right now.</p>'}</div>
              </div>
              <div class="rule-top joinbar">
                <span class="lab">Join room</span>
                <input type="text" id="joinRoomCode" placeholder="ROOM CODE" maxlength="6" style="max-width:160px;text-transform:uppercase" />
                <button id="joinRoomBtn" class="btn-primary">Join</button>
              </div>
            </div>

            <div>
              <div class="box pad">
                <h3>Lobby stats</h3>
                <div class="stats mt-16" style="grid-template-columns:1fr 1fr">
                  <div class="stat"><div class="k">Players online</div><div class="v">${stats.total_players}/${stats.max_players}</div></div>
                  <div class="stat"><div class="k">Active games</div><div class="v">${stats.active_games}</div></div>
                </div>
              </div>
              <div class="box pad mt-24">
                <h3>Leaderboard</h3>
                <div class="scroll-x mt-16">${renderLeaderboardTable()}</div>
              </div>
            </div>
          </div>

          ${state.isAdmin ? renderAdminPanel() : ''}
        `;
    }

    function renderLeaderboardTable() {
        if (!leaderboard.length) return '<p>No players yet.</p>';
        const rows = leaderboard.map(en => `
          <tr>
            <td class="num">#${en.rank}</td>
            <td>${escapeHTML(en.player_name)}</td>
            <td class="num">${en.total_score}</td>
          </tr>
        `).join('');
        return `<table class="data"><thead><tr><th class="num">Rank</th><th>Player</th><th class="num">Score</th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    function renderAdminPanel() {
        const rows = allGameSettings.map(s => `
          <div class="setting-row">
            <label>${GAME_LABELS[s.game_name] || s.game_name}</label>
            <input type="checkbox" data-toggle-game="${s.game_name}" ${s.enabled ? 'checked' : ''} />
            <span class="text-dim text-mono" style="font-size:11px">${s.enabled ? 'enabled' : 'disabled'}</span>
          </div>
        `).join('');

        return `
          <section class="panel box admin-panel-box">
            <div class="panel-h">Admin — game visibility</div>
            ${rows || '<div class="pad text-dim">No games configured.</div>'}
            <div class="pad rule-top">
              <div class="flex-row">
                <button id="adminStartTwoThirds" class="btn-sm">Start two-thirds</button>
                <button id="adminStartFishPond" class="btn-sm">Start fish pond</button>
              </div>
            </div>
            <div class="panel-h rule-top">Admin — players</div>
            <div class="pad" id="adminPlayerMgmt">Loading…</div>
          </section>
        `;
    }

    function wireCatalog() {
        document.querySelectorAll('.card[data-game]').forEach(card => {
            card.addEventListener('click', async () => {
                const gameName = card.dataset.game;
                const meta = GAME_META[gameName];
                if (!meta.createLabel) {
                    navigate(meta.route);
                    return;
                }
                const maxPlayers = gameName === 'market' ? 6 : undefined;
                try {
                    const r = await apiCall('/rooms/create', 'POST', {
                        player_id: state.currentPlayer.id,
                        game_name: gameName,
                        max_players: maxPlayers,
                    });
                    setRoomCode(r.room_code);
                    room = r;
                    render();
                } catch (error) {
                    showNotification(error.message, 'error');
                }
            });
        });

        document.getElementById('joinRoomBtn').addEventListener('click', async () => {
            const codeInput = document.getElementById('joinRoomCode');
            const code = codeInput.value.trim().toUpperCase();
            if (!code) { showNotification('Enter a room code', 'error'); return; }
            try {
                const r = await apiCall('/rooms/join', 'POST', { player_id: state.currentPlayer.id, room_code: code });
                setRoomCode(r.room_code);
                room = r;
                render();
            } catch (error) {
                showNotification(error.message, 'error');
            }
        });

        if (state.isAdmin) {
            document.querySelectorAll('[data-toggle-game]').forEach(cb => {
                cb.addEventListener('change', async () => {
                    const gameName = cb.dataset.toggleGame;
                    try {
                        await apiCall(`/games/settings/${gameName}`, 'PUT', { game_name: gameName, enabled: cb.checked });
                        showNotification(`${GAME_LABELS[gameName] || gameName} visibility updated`, 'success');
                        await loadAll();
                        render();
                    } catch (error) {
                        showNotification(error.message, 'error');
                    }
                });
            });
            document.getElementById('adminStartTwoThirds')?.addEventListener('click', () => startAdminGame('two-thirds'));
            document.getElementById('adminStartFishPond')?.addEventListener('click', () => startAdminGame('fish-pond'));
            loadPlayerManagement();
        }
    }

    async function startAdminGame(slug) {
        try {
            await apiCall(`/games/${slug}/start`, 'POST');
            showNotification('Game started', 'success');
        } catch (error) {
            showNotification(error.message, 'error');
        }
    }

    async function loadPlayerManagement() {
        try {
            const players = await apiCall('/players');
            if (disposed) return;
            const box = document.getElementById('adminPlayerMgmt');
            if (!box) return;
            if (!players.length) { box.innerHTML = '<p class="text-dim">No players registered.</p>'; return; }
            const rows = players.map(p => `
              <tr>
                <td>${escapeHTML(p.name)}</td>
                <td class="num text-amber">${escapeHTML(p.passcode || '—')}</td>
                <td class="num">${p.total_score}</td>
                <td class="num"><button class="btn-sm btn-danger" data-delete-player="${p.id}" data-name="${escapeHTML(p.name)}">Delete</button></td>
              </tr>
            `).join('');
            box.innerHTML = `
              <div class="scroll-x"><table class="data"><thead><tr><th>Name</th><th class="num">PIN</th><th class="num">Score</th><th class="num"></th></tr></thead><tbody>${rows}</tbody></table></div>
              <div class="flex-row mt-16">
                <button id="resetScores" class="btn-sm">Reset all scores</button>
                <button id="clearAllPlayers" class="btn-sm btn-danger">Delete all players</button>
              </div>
            `;
            box.querySelectorAll('[data-delete-player]').forEach(btn => {
                btn.addEventListener('click', async () => {
                    if (!confirm(`Delete player "${btn.dataset.name}"?`)) return;
                    try {
                        await apiCall(`/players/${btn.dataset.deletePlayer}`, 'DELETE');
                        showNotification('Player deleted', 'success');
                        await refresh();
                    } catch (error) {
                        showNotification(error.message, 'error');
                    }
                });
            });
            document.getElementById('resetScores').addEventListener('click', async () => {
                if (!confirm("Reset all players' scores to 0?")) return;
                try {
                    await apiCall('/players/reset-scores', 'POST');
                    showNotification('Scores reset', 'success');
                    await refresh();
                } catch (error) { showNotification(error.message, 'error'); }
            });
            document.getElementById('clearAllPlayers').addEventListener('click', async () => {
                if (!confirm('Delete ALL players? This cannot be undone.')) return;
                try {
                    await apiCall('/players/clear-all', 'POST');
                    showNotification('All players deleted', 'success');
                    await refresh();
                } catch (error) { showNotification(error.message, 'error'); }
            });
        } catch {
            // admin token expired mid-session — ignore, rail will reflect it on next check
        }
    }

    // ---------------- Lobby (waiting room) ----------------

    function renderLobby(r) {
        const members = r.members.map(m => `
          <tr>
            <td>${escapeHTML(m.player_name)} ${m.player_id === r.host_id ? '<span class="chip host">host</span>' : ''}</td>
            <td class="num">${m.is_ready ? '<span class="text-amber">ready</span>' : '<span class="text-dim">waiting</span>'}</td>
          </tr>
        `).join('');
        const isHostPlayer = state.currentPlayer.id === r.host_id;
        const me = r.members.find(m => m.player_id === state.currentPlayer.id);
        const iAmReady = me ? me.is_ready : false;
        const minPlayers = r.game_name === 'market' ? 1 : 2;
        const allReady = r.members.every(m => m.is_ready);
        const canStart = allReady && r.members.length >= minPlayers;
        const shareUrl = `${window.location.origin}/r/${r.room_code}`;

        return `
          <div class="box">
            <div class="pad">
              <div class="eyebrow">${escapeHTML(GAME_LABELS[r.game_name] || r.game_name)}</div>
              <div class="room-code-badge">${escapeHTML(r.room_code)}</div>
              <p class="mt-16">Host: ${escapeHTML(r.host_name || '—')}</p>
            </div>
            <div class="rule-top joinbar">
              <span class="lab">Invite</span>
              <div class="linkbox">${escapeHTML(shareUrl)}</div>
              <button id="copyInvite" class="btn-sm">Copy link</button>
            </div>
            <div class="rule-top pad">
              <h3>Players joined</h3>
              <table class="data mt-16"><thead><tr><th>Player</th><th class="num">Status</th></tr></thead><tbody>${members}</tbody></table>
            </div>
            <div class="rule-top pad flex-row">
              <button id="toggleReady" class="${iAmReady ? '' : 'btn-primary'}">${iAmReady ? 'Set not ready' : 'Set ready'}</button>
              ${isHostPlayer ? `<button id="startGame" class="btn-primary" ${canStart ? '' : 'disabled'}>Start game</button>` : ''}
              <span class="spacer"></span>
              <button id="leaveRoom" class="btn-danger">Leave room</button>
            </div>
          </div>
        `;
    }

    function wireLobby() {
        document.getElementById('copyInvite')?.addEventListener('click', async () => {
            const url = `${window.location.origin}/r/${room.room_code}`;
            try {
                await navigator.clipboard.writeText(url);
                showNotification('Invite link copied', 'success');
            } catch {
                showNotification(url, 'info');
            }
        });
        document.getElementById('toggleReady').addEventListener('click', async () => {
            const me = room.members.find(m => m.player_id === state.currentPlayer.id);
            const next = !(me && me.is_ready);
            try {
                await apiCall(`/rooms/${room.room_code}/ready?player_id=${state.currentPlayer.id}&is_ready=${next}`, 'POST');
                await loadRoom();
                render();
            } catch (error) { showNotification(error.message, 'error'); }
        });
        document.getElementById('startGame')?.addEventListener('click', async () => {
            try {
                await apiCall(`/rooms/${room.room_code}/start?host_id=${state.currentPlayer.id}`, 'POST');
                showNotification('Starting game…', 'success');
            } catch (error) { showNotification(error.message, 'error'); }
        });
        document.getElementById('leaveRoom').addEventListener('click', async () => {
            try {
                await apiCall(`/rooms/${room.room_code}/leave?player_id=${state.currentPlayer.id}`, 'POST');
                setRoomCode(null);
                room = null;
                render();
            } catch (error) { showNotification(error.message, 'error'); }
        });
    }

    // ---------------- Lifecycle ----------------

    el.innerHTML = '<p class="text-dim pad">Loading…</p>';
    refresh();

    const unsubLobby = onLobby((data) => {
        if (disposed) return;
        if (data.event === 'player_registered') {
            loadAll().then(() => { if (!disposed) render(); });
        } else if (data.event === 'settings_updated') {
            loadAll().then(() => { if (!disposed) render(); });
        } else if (data.event === 'lobby_updated') {
            if (state.currentRoomCode && data.room_code === state.currentRoomCode) {
                loadRoom().then(() => { if (!disposed) render(); });
            }
        } else if (data.event === 'game_started') {
            if (state.currentRoomCode && data.room_code === state.currentRoomCode) {
                setRoomCode(null);
                checkRedirectToActiveGame();
            } else {
                loadAll().then(() => { if (!disposed) render(); });
            }
        }
    });

    return () => {
        disposed = true;
        unsubLobby();
    };
}
