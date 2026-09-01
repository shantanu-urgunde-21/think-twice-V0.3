// views/fishPond.js

import { apiCall, escapeHTML } from '../api.js';
import { state, setRoomCode } from '../store.js';
import { connectGame, disconnectGame, onGame } from '../socket.js';
import { navigate } from '../router.js';
import { showNotification } from '../shell.js';

export async function renderFishPond(el) {
    let disposed = false;

    if (!state.currentPlayer) {
        el.innerHTML = `<div class="state-msg">Register or log in from <a href="/" class="text-amber">Games</a> first.</div>`;
        return () => {};
    }

    let activeInfo;
    try {
        activeInfo = await apiCall(`/rooms/active-player-game/${state.currentPlayer.id}`);
    } catch {
        activeInfo = null;
    }
    if (!activeInfo || activeInfo.game_name !== 'fish_pond') {
        el.innerHTML = `<div class="state-msg">No active Fish Pond game. Create or join a room from <a href="/" class="text-amber">Games</a>.</div>`;
        return () => {};
    }

    const gameId = activeInfo.game_id;
    const roomCode = activeInfo.room_code;
    let isHost = false;
    try {
        const roomDetails = await apiCall(`/rooms/${roomCode}`);
        isHost = state.currentPlayer.id === roomDetails.host_id;
    } catch { /* non-fatal */ }

    connectGame(gameId);

    let game = { current_round: 1, max_rounds: 5, current_fish: 100, submissions_count: 0, collapsed: false };
    let catchQty = 10;
    let hasSubmitted = false;
    let results = null;

    async function loadDetails() {
        try {
            game = await apiCall(`/games/fish-pond/${gameId}/details`);
        } catch (e) {
            console.error('Error loading fish pond details:', e);
        }
    }

    function render() {
        const canManage = isHost || state.isAdmin;

        el.innerHTML = `
          <div class="section-head"><h2>Fish Pond</h2></div>
          <div class="box pad" style="max-width:560px">
            <p>The pond starts with 100 fish, shared with the room. Each round you choose how many to catch (0-20); the rest regenerate by 50%.</p>
            <p class="text-amber mt-16" style="font-size:13px">If the total catch exceeds what's in the pond, it collapses and the game ends immediately.</p>

            <div class="stats mt-24" style="grid-template-columns:1fr 1fr">
              <div class="stat"><div class="k">Round</div><div class="v">${game.current_round} / ${game.max_rounds}</div></div>
              <div class="stat"><div class="k">Fish in pond</div><div class="v amber">${game.current_fish}</div></div>
            </div>

            ${game.collapsed ? `<div class="state-msg error mt-24"><strong>The pond has collapsed.</strong> The game is over.</div>` : ''}

            ${!game.collapsed && !hasSubmitted && !results ? `
              <form id="catchForm" class="mt-24">
                <div>
                  <label for="catchInput">Your catch: <span class="text-amber" id="catchVal">${catchQty}</span> fish</label>
                  <input type="range" id="catchInput" min="0" max="20" value="${catchQty}" />
                </div>
                <button type="submit" class="btn-primary btn-block">Submit catch</button>
              </form>
            ` : ''}

            ${!game.collapsed && hasSubmitted && !results ? `
              <div class="mt-24">
                <p>Waiting on other players — <span class="text-amber">${game.submissions_count}</span> submitted this round.</p>
                ${canManage ? `
                  <div class="flex-row mt-16">
                    <button id="calcBtn" class="btn-primary">Calculate round</button>
                    <button id="closeBtn" class="btn-danger">Close game</button>
                  </div>
                ` : ''}
              </div>
            ` : ''}

            ${results ? renderResults() : ''}
          </div>
          <button id="leaveGameBtn" class="btn-danger mt-24">Leave game</button>
        `;
        wire();
    }

    function renderResults() {
        const rows = results.all_submissions.map(s => `
          <tr><td>${escapeHTML(s.player_name)}</td><td class="num">${s.fish_caught}</td></tr>
        `).join('');
        return `
          <div class="result-box mt-24">
            <h3>Round results</h3>
            <p>Initial: ${results.initial_fish} · caught: ${results.total_caught} · remaining: ${results.remaining_fish}</p>
            ${results.collapsed
                ? `<p class="text-mono" style="color:var(--sell)" class="mt-16"><strong>The pond has collapsed.</strong></p>`
                : `<p class="text-amber mt-16">+${results.regeneration} regenerated → ${results.current_fish} fish for next round</p>`}
            <div class="scroll-x mt-16">
              <table class="data"><thead><tr><th>Player</th><th class="num">Catch</th></tr></thead><tbody>${rows}</tbody></table>
            </div>
          </div>
        `;
    }

    function wire() {
        const range = document.getElementById('catchInput');
        range?.addEventListener('input', () => {
            document.getElementById('catchVal').textContent = range.value;
        });

        document.getElementById('catchForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            catchQty = parseInt(document.getElementById('catchInput').value, 10);
            try {
                await apiCall(`/games/fish-pond/${gameId}/submit`, 'POST', { player_id: state.currentPlayer.id, fish_caught: catchQty });
                hasSubmitted = true;
                showNotification('Catch submitted — waiting for others…', 'success');
                render();
            } catch (error) { showNotification(error.message, 'error'); }
        });

        document.getElementById('calcBtn')?.addEventListener('click', async () => {
            try {
                results = await apiCall(`/games/fish-pond/${gameId}/calculate?host_id=${state.currentPlayer.id}`, 'POST');
                render();
            } catch (error) { showNotification(error.message, 'error'); }
        });

        document.getElementById('closeBtn')?.addEventListener('click', async () => {
            if (!confirm("Close this game? Players won't be able to catch anymore.")) return;
            try {
                await apiCall(`/games/fish-pond/${gameId}/close?host_id=${state.currentPlayer.id}`, 'POST');
                showNotification('Game closed', 'success');
                setRoomCode(null);
                navigate('/');
            } catch (error) { showNotification(error.message, 'error'); }
        });

        document.getElementById('leaveGameBtn')?.addEventListener('click', async () => {
            const confirmMsg = isHost
                ? 'You are the host. Leaving may transfer host privileges or close the room. Continue?'
                : 'Leave this game?';
            if (!confirm(confirmMsg)) return;
            try {
                await apiCall(`/rooms/${roomCode}/leave?player_id=${state.currentPlayer.id}`, 'POST');
            } catch { /* room may already be gone */ }
            setRoomCode(null);
            navigate('/');
        });
    }

    const unsubGame = onGame((data) => {
        if (disposed) return;
        if (data.event === 'submission') {
            game.submissions_count = data.submissions_count;
            render();
        } else if (data.event === 'round_calculated') {
            showNotification('Round calculated by admin', 'success');
            hasSubmitted = false;
            loadDetails().then(() => { if (!disposed) render(); });
        } else if (data.event === 'game_closed') {
            showNotification('Game closed by admin', 'info');
            setRoomCode(null);
            setTimeout(() => navigate('/'), 1200);
        }
    });

    await loadDetails();
    if (!disposed) render();

    return () => {
        disposed = true;
        unsubGame();
        disconnectGame();
    };
}
