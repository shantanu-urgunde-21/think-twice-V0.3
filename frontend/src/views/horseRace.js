// views/horseRace.js — solo, offline. No room, no WebSocket.

import { apiCall, escapeHTML } from '../api.js';
import { state } from '../store.js';
import { showNotification } from '../shell.js';

export async function renderHorseRace(el) {
    let disposed = false;

    if (!state.currentPlayer) {
        el.innerHTML = `<div class="state-msg">Register or log in from <a href="/" class="text-amber">Games</a> first.</div>`;
        return () => {};
    }

    let gameId = null;
    let allHorses = [];
    let selected = [];
    let roundNumber = 1;
    let raceResults = null;
    let finalResult = null;

    el.innerHTML = '<p class="text-dim pad">Loading…</p>';

    try {
        const status = await apiCall(`/games/horse-race/player-status/${state.currentPlayer.id}`);
        if (!status.can_play) {
            el.innerHTML = `<div class="state-msg error">You've completed the maximum 2 Horse Race games and can't play again.</div>`;
            return () => {};
        }
        if (status.games_remaining <= 1 && status.games_completed > 0) {
            showNotification(`Warning: you have ${status.games_remaining} game(s) remaining.`, 'info');
        }

        const result = await apiCall('/games/horse-race/start', 'POST', { player_id: state.currentPlayer.id });
        gameId = result.game_id;
        allHorses = await apiCall(`/games/horse-race/${gameId}/horses`);
    } catch (error) {
        el.innerHTML = `<div class="state-msg error">${escapeHTML(error.message)}</div>`;
        return () => {};
    }

    if (disposed) return () => {};

    function render() {
        if (finalResult) { renderFinal(); return; }

        const horseCells = allHorses.map(h => `
          <button type="button" class="horse-item ${selected.includes(h.id) ? 'selected' : ''}" data-horse="${h.id}">${escapeHTML(h.name)}</button>
        `).join('');

        el.innerHTML = `
          <div class="section-head"><h2>Horse Racing</h2><span class="note">round ${roundNumber}</span></div>
          <div class="box pad">
            <p>Identify the 3 fastest horses out of 25 in as few rounds as possible. Each round, race 5 horses; scoring is 50 points minus 5 per round used, minimum 10.</p>

            ${!raceResults ? `
              <h3 class="mt-16">Select 5 horses to race</h3>
              <div class="horse-grid mt-16">${horseCells}</div>
              <button id="raceBtn" class="btn-primary mt-16" ${selected.length === 5 ? '' : 'disabled'}>Race horses</button>
            ` : `
              <h3 class="mt-16">Race results (by finish position)</h3>
              <ol class="mt-16" style="padding-left:20px;color:var(--ink)">
                ${raceResults.race_results.map(h => `<li>${escapeHTML(h.name)} — position ${h.position}</li>`).join('')}
              </ol>
              <p class="text-amber mt-16">${escapeHTML(raceResults.message)}</p>
              <button id="nextRoundBtn" class="btn-primary mt-16">Next round</button>
            `}

            <div class="rule-top pad" style="margin:16px -16px -16px;padding:14px 16px">
              <h3>Submit your answer</h3>
              <p>Think you know the top 3? Submit in order.</p>
              <div class="flex-row mt-16">
                <select id="firstSel"></select>
                <select id="secondSel"></select>
                <select id="thirdSel"></select>
              </div>
              <button id="submitTopThreeBtn" class="btn-primary mt-16">Submit top 3</button>
            </div>
          </div>
        `;

        ['firstSel', 'secondSel', 'thirdSel'].forEach(id => {
            const select = document.getElementById(id);
            select.innerHTML = '<option value="">Select…</option>' + allHorses.map(h => `<option value="${h.id}">${escapeHTML(h.name)}</option>`).join('');
        });

        wire();
    }

    function renderFinal() {
        el.innerHTML = `
          <div class="section-head"><h2>Horse Racing — result</h2></div>
          <div class="box pad">
            ${finalResult.correct ? `
              <h3 class="text-amber" style="text-transform:none;letter-spacing:0;font-size:18px">Correct!</h3>
              <p class="mt-16">You earned <strong class="text-amber">${finalResult.score}</strong> points in ${finalResult.rounds_used} round(s).</p>
              <h4 class="mt-24">The actual top 3:</h4>
              <ol class="mt-16" style="padding-left:20px;color:var(--ink)">
                ${finalResult.actual_top_three.map(h => `<li>${escapeHTML(h.name)}</li>`).join('')}
              </ol>
            ` : `
              <h3 style="color:var(--sell);text-transform:none;letter-spacing:0;font-size:18px">Not quite</h3>
              <p class="mt-16">${escapeHTML(finalResult.message)}</p>
            `}
          </div>
          <a href="/" class="btn-danger mt-24" style="display:inline-flex">Back to games</a>
        `;
    }

    function wire() {
        el.querySelectorAll('[data-horse]').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.horse, 10);
                if (selected.includes(id)) {
                    selected = selected.filter(x => x !== id);
                } else if (selected.length < 5) {
                    selected.push(id);
                } else {
                    showNotification('You can only select 5 horses', 'error');
                    return;
                }
                render();
            });
        });

        document.getElementById('raceBtn')?.addEventListener('click', async () => {
            try {
                const result = await apiCall(`/games/horse-race/${gameId}/race`, 'POST', {
                    player_id: state.currentPlayer.id,
                    selected_horse_ids: selected,
                });
                roundNumber = result.round_number;
                raceResults = result;
                render();
            } catch (error) { showNotification(error.message, 'error'); }
        });

        document.getElementById('nextRoundBtn')?.addEventListener('click', () => {
            selected = [];
            raceResults = null;
            render();
        });

        document.getElementById('submitTopThreeBtn')?.addEventListener('click', async () => {
            const first = parseInt(document.getElementById('firstSel').value, 10);
            const second = parseInt(document.getElementById('secondSel').value, 10);
            const third = parseInt(document.getElementById('thirdSel').value, 10);
            if (!first || !second || !third) { showNotification('Select all three horses', 'error'); return; }
            if (new Set([first, second, third]).size !== 3) { showNotification('Select three different horses', 'error'); return; }
            try {
                finalResult = await apiCall(`/games/horse-race/${gameId}/submit-top-three`, 'POST', {
                    player_id: state.currentPlayer.id,
                    top_three_ids: [first, second, third],
                });
                render();
            } catch (error) { showNotification(error.message, 'error'); }
        });
    }

    render();

    return () => { disposed = true; };
}
