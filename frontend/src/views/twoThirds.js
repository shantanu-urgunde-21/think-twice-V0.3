// views/twoThirds.js

import { apiCall, escapeHTML } from '../api.js';
import { state, setRoomCode } from '../store.js';
import { connectGame, disconnectGame, onGame } from '../socket.js';
import { navigate } from '../router.js';
import { showNotification } from '../shell.js';

export async function renderTwoThirds(el) {
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
    if (!activeInfo || activeInfo.game_name !== 'two_thirds') {
        el.innerHTML = `<div class="state-msg">No active 2/3-Average game. Create or join a room from <a href="/" class="text-amber">Games</a>.</div>`;
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

    let submissionCount = 0;
    let hasSubmitted = false;
    let results = null;

    try {
        const round = await apiCall(`/games/two-thirds/${gameId}/current-round`);
        submissionCount = round.submissions_count;
    } catch { /* fine — falls through to render */ }

    function render() {
        const canManage = isHost || state.isAdmin;

        el.innerHTML = `
          <div class="section-head"><h2>2/3 of the Average</h2></div>
          <div class="box pad" style="max-width:520px">
            <p>Guess a number from 0 to 100. Whoever is closest to two-thirds of the group's average wins 10 points; everyone else gets 1 for playing.</p>

            ${!hasSubmitted && !results ? `
              <form id="guessForm" class="mt-24">
                <div>
                  <label for="guessInput">Your guess (0-100)</label>
                  <input type="number" id="guessInput" min="0" max="100" required />
                </div>
                <button type="submit" class="btn-primary btn-block">Submit guess</button>
              </form>
            ` : ''}

            ${hasSubmitted && !results ? `
              <div class="mt-24">
                <p>Waiting on other players — <span class="text-amber">${submissionCount}</span> submitted.</p>
                ${canManage ? `
                  <div class="flex-row mt-16">
                    <button id="calcBtn" class="btn-primary">Calculate results</button>
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
        const rows = results.all_guesses.map(g => `
          <tr><td>${escapeHTML(g.player_name)}</td><td class="num">${g.guess}</td><td class="num">${g.distance.toFixed(2)}</td><td class="num">${g.points}</td></tr>
        `).join('');
        return `
          <div class="result-box mt-24">
            <h3>Results</h3>
            <p>Average: ${results.average.toFixed(2)} · 2/3 of average: ${results.two_thirds_average.toFixed(2)}</p>
            <p class="text-amber mt-16">Winner: ${escapeHTML(results.winner_name)}</p>
            <div class="scroll-x mt-16">
              <table class="data"><thead><tr><th>Player</th><th class="num">Guess</th><th class="num">Distance</th><th class="num">Points</th></tr></thead><tbody>${rows}</tbody></table>
            </div>
          </div>
        `;
    }

    function wire() {
        document.getElementById('guessForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const guess = parseInt(document.getElementById('guessInput').value, 10);
            try {
                await apiCall(`/games/two-thirds/${gameId}/submit`, 'POST', { player_id: state.currentPlayer.id, guess });
                hasSubmitted = true;
                showNotification('Guess submitted — waiting for others…', 'success');
                render();
            } catch (error) { showNotification(error.message, 'error'); }
        });

        document.getElementById('calcBtn')?.addEventListener('click', async () => {
            try {
                results = await apiCall(`/games/two-thirds/${gameId}/calculate?host_id=${state.currentPlayer.id}`, 'POST');
                render();
            } catch (error) { showNotification(error.message, 'error'); }
        });

        document.getElementById('closeBtn')?.addEventListener('click', async () => {
            if (!results) { showNotification('Calculate results before closing the game', 'error'); return; }
            if (!confirm("Close this game? Players won't be able to submit anymore.")) return;
            try {
                await apiCall(`/games/two-thirds/${gameId}/close?host_id=${state.currentPlayer.id}`, 'POST');
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
            submissionCount = data.submissions_count;
            render();
        } else if (data.event === 'results_calculated') {
            apiCall(`/games/two-thirds/${gameId}/calculate?host_id=${state.currentPlayer.id}`, 'POST')
                .then(r => { results = r; if (!disposed) render(); })
                .catch(() => {});
        } else if (data.event === 'game_closed') {
            showNotification('Game closed by admin', 'info');
            setRoomCode(null);
            setTimeout(() => navigate('/'), 1200);
        }
    });

    render();

    return () => {
        disposed = true;
        unsubGame();
        disconnectGame();
    };
}
