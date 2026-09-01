// views/market.js — Hidden Market. The flagship view: real price history
// chart, the private signal, a BUY/SELL/HOLD console, and a round log built
// from data the API actually returns (no fabricated instance/seq telemetry —
// those land here once Phases 3 and 5 exist to back them).

import { apiCall, escapeHTML } from '../api.js';
import { state, setRoomCode } from '../store.js';
import { connectGame, disconnectGame, onGame, status as socketStatus } from '../socket.js';
import { navigate } from '../router.js';
import { showNotification } from '../shell.js';

export async function renderMarket(el) {
    let disposed = false;
    let gameId = null;
    let roomCode = null;
    let isHost = false;
    let view = null;
    let selectedAction = 'HOLD';
    let qty = 1;
    let lastRoundResult = null;
    let roundLog = [];
    let resolving = false;
    let lastResolveMs = null;

    // The host both triggers resolve (direct HTTP response) and receives the
    // WS broadcast of that same round — dedupe so the log doesn't double up.
    function pushRoundLog(entry) {
        const last = roundLog[roundLog.length - 1];
        if (last && last.round_number === entry.round_number) return;
        roundLog.push(entry);
    }

    el.innerHTML = '<p class="text-dim pad">Loading…</p>';

    let activeInfo;
    try {
        activeInfo = await apiCall(`/rooms/active-player-game/${state.currentPlayer?.id}`);
    } catch {
        activeInfo = null;
    }

    if (!state.currentPlayer) {
        el.innerHTML = `<div class="state-msg">Register or log in from <a href="/" class="text-amber">Games</a> first.</div>`;
        return () => {};
    }

    if (!activeInfo || activeInfo.game_name !== 'market') {
        el.innerHTML = `<div class="state-msg">No active Hidden Market game. Create or join a room from <a href="/" class="text-amber">Games</a>.</div>`;
        return () => {};
    }

    gameId = activeInfo.game_id;
    roomCode = activeInfo.room_code;

    try {
        const roomDetails = await apiCall(`/rooms/${roomCode}`);
        isHost = state.currentPlayer.id === roomDetails.host_id;
    } catch { /* non-fatal */ }

    connectGame(gameId);

    async function refreshView() {
        try {
            const v = await apiCall(`/games/market/${gameId}/view/${state.currentPlayer.id}`);
            view = v;
        } catch (e) {
            console.error('Error loading market view:', e);
        }
    }

    function delta() {
        if (!view || view.price_history.length < 2) return { text: '—', cls: 'flat' };
        const prev = view.price_history[view.price_history.length - 2];
        const d = view.price - prev;
        const cls = d > 0 ? 'up' : d < 0 ? 'down' : 'flat';
        const arrow = d > 0 ? '▲' : d < 0 ? '▼' : '·';
        return { text: `${arrow} ${d >= 0 ? '+' : ''}${d.toFixed(2)}`, cls };
    }

    function renderChart() {
        const hist = view.price_history;
        const w = 600, h = 114, padL = 40, padR = 12, padT = 8, padB = 20;
        const plotW = w - padL - padR, plotH = h - padT - padB;
        const min = Math.min(...hist), max = Math.max(...hist);
        const range = Math.max(max - min, 1);
        const lo = min - range * 0.15, hi = max + range * 0.15;

        const xAt = (i) => padL + (hist.length > 1 ? (i / (hist.length - 1)) * plotW : 0);
        const yAt = (v) => padT + plotH - ((v - lo) / (hi - lo)) * plotH;

        const pts = hist.map((v, i) => [xAt(i), yAt(v)]);
        const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
        const areaPath = `${linePath} L${pts[pts.length - 1][0].toFixed(1)},${(padT + plotH).toFixed(1)} L${pts[0][0].toFixed(1)},${(padT + plotH).toFixed(1)} Z`;

        const gridLines = [0, 0.5, 1].map(f => {
            const y = padT + plotH * f;
            const val = hi - (hi - lo) * f;
            return `<line x1="${padL}" y1="${y}" x2="${w - padR}" y2="${y}" stroke="var(--line-soft)" stroke-width="1"/>
                    <text x="${padL - 6}" y="${y + 3}" fill="var(--ink-dim)" font-family="var(--mono)" font-size="9" text-anchor="end">${val.toFixed(2)}</text>`;
        }).join('');

        const dots = pts.map((p, i) => {
            const isLast = i === pts.length - 1;
            return `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="${isLast ? 4 : 2.2}" fill="${isLast ? 'var(--amber)' : 'var(--surface)'}" stroke="var(--amber-dim)" stroke-width="${isLast ? 0 : 1.3}"/>`;
        }).join('');

        const xLabels = hist.map((_, i) => {
            const label = i === 0 ? 'open' : `${i}`;
            return `<text x="${xAt(i).toFixed(1)}" y="${h - 4}" fill="var(--ink-faint)" font-family="var(--mono)" font-size="9" text-anchor="middle">${label}</text>`;
        }).join('');

        return `
          <svg class="chart-svg" viewBox="0 0 ${w} ${h}" role="img" aria-label="Price history over ${hist.length} rounds, currently ${view.price.toFixed(2)}">
            ${gridLines}
            <path d="${areaPath}" fill="var(--amber)" fill-opacity="0.08" stroke="none"/>
            <path d="${linePath}" fill="none" stroke="var(--amber)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
            ${dots}
            ${xLabels}
          </svg>
        `;
    }

    function render() {
        if (!view) { el.innerHTML = '<p class="text-dim pad">Loading…</p>'; return; }

        if (view.finished) {
            renderFinal();
            return;
        }

        const d = delta();
        const affordable = view.price > 0 ? Math.floor(view.cash / view.price) : 0;

        el.innerHTML = `
          <div class="section-head">
            <h2>Hidden Market</h2>
            <span class="note">round ${view.round_number} / ${view.max_rounds}</span>
          </div>

          <div class="grid-2">
            <div class="box">
              <div class="mkt-top">
                <div class="ticker">
                  <h3>Commodity · spot</h3>
                  <div class="price">${view.price.toFixed(2)}</div>
                  <div class="delta ${d.cls}">${d.text}</div>
                </div>
              </div>

              <div class="chart-wrap">${renderChart()}</div>

              <div class="stats mt-24">
                <div class="stat"><div class="k">Cash</div><div class="v">${view.cash.toFixed(2)}</div></div>
                <div class="stat"><div class="k">Inventory</div><div class="v">${view.inventory}</div></div>
                <div class="stat"><div class="k">Equity</div><div class="v">${(view.cash + view.inventory * view.price).toFixed(2)}</div></div>
                <div class="stat"><div class="k">Submitted</div><div class="v">${view.submissions_count} / ${view.total_players}</div></div>
              </div>

              <div class="signal mt-24" style="margin-top:24px">
                <div>
                  <div class="lab">Your signal</div>
                  <div class="val">${view.private_signal > 0 ? '+' : ''}${view.private_signal.toFixed(2)}</div>
                </div>
                <p class="exp">A noisy read on the coming move — positive leans up, negative leans down. Only you can see this.</p>
              </div>

              ${view.has_submitted ? renderWaiting() : renderConsole(affordable)}

              ${lastRoundResult ? renderRoundResult() : ''}
            </div>

            <aside class="box">
              <div class="panel-h">Engine <span class="n">${socketStatus.game === 'live' ? 'connected' : socketStatus.game}</span></div>
              <div class="pad" style="font-family:var(--mono);font-size:12px;color:var(--ink-mid);display:flex;flex-direction:column;gap:8px">
                <div class="flex-row"><span class="text-dim">socket</span><span class="spacer"></span><span class="${socketStatus.game === 'live' ? 'text-amber' : ''}">${socketStatus.game}</span></div>
                ${lastResolveMs !== null ? `<div class="flex-row"><span class="text-dim">last resolve</span><span class="spacer"></span><span>${lastResolveMs}ms</span></div>` : ''}
                <div class="flex-row"><span class="text-dim">host</span><span class="spacer"></span><span>${isHost ? 'you' : 'other player'}</span></div>
              </div>

              <div class="panel-h rule-top">Round log</div>
              <div class="log">
                ${roundLog.length ? roundLog.slice().reverse().map(rl => `
                  <div class="ev"><span class="ty">round ${rl.round_number} resolved</span><span class="dt">${rl.price_before.toFixed(2)} → ${rl.price_after.toFixed(2)}</span></div>
                `).join('') : '<div class="ev"><span class="ty text-dim">no rounds resolved yet</span></div>'}
              </div>
            </aside>
          </div>

          <button id="leaveGameBtn" class="btn-danger mt-24">Leave game</button>
        `;
        wire(affordable);
    }

    function renderConsole(affordable) {
        const est = selectedAction === 'HOLD'
            ? 'no trade'
            : selectedAction === 'BUY'
                ? `~${(qty * view.price).toFixed(2)} cost · buying power ${affordable} @ ${view.price.toFixed(2)}`
                : `~${(qty * view.price).toFixed(2)} proceeds · you hold ${view.inventory}`;

        return `
          <div class="pad rule-top">
            <div class="console">
              <button class="act btn-buy ${selectedAction === 'BUY' ? 'on' : ''}" data-action="BUY">BUY</button>
              <button class="act btn-sell ${selectedAction === 'SELL' ? 'on' : ''}" data-action="SELL">SELL</button>
              <button class="act btn-hold ${selectedAction === 'HOLD' ? 'on' : ''}" data-action="HOLD">HOLD</button>
              <div class="qty" style="${selectedAction === 'HOLD' ? 'display:none' : ''}">
                <button type="button" id="qtyDown">−</button>
                <input type="number" id="qtyInput" min="1" value="${qty}" />
                <button type="button" id="qtyUp">+</button>
              </div>
              <button id="submitAction" class="btn-primary">Submit</button>
            </div>
            <p class="text-mono text-dim mt-16" style="font-size:11.5px">${est}</p>
          </div>
        `;
    }

    function renderWaiting() {
        const canResolve = isHost || state.isAdmin;
        return `
          <div class="pad rule-top">
            <p>Waiting on other traders — <span class="text-amber">${view.submissions_count} / ${view.total_players}</span> submitted.</p>
            ${canResolve ? `<button id="resolveRoundBtn" class="btn-primary mt-16" ${resolving ? 'disabled' : ''}>${resolving ? 'Resolving…' : 'Resolve round'}</button>` : `<p class="text-dim mt-16" style="font-size:12.5px">Waiting for the host to resolve the round.</p>`}
          </div>
        `;
    }

    function renderRoundResult() {
        const trades = lastRoundResult.trades.map(t => {
            const label = t.player_id === -1 ? 'AI · trend follower' : (t.player_id === state.currentPlayer.id ? 'You' : `Player #${t.player_id}`);
            const tagClass = t.type === 'BUY' ? 'tag-b' : t.type === 'SELL' ? 'tag-s' : 'tag-h';
            return `<tr${t.player_id === state.currentPlayer.id ? ' class="you"' : ''}><td>${label}</td><td class="${tagClass}">${t.type}</td><td class="num">${t.qty || '—'}</td><td class="num">${t.fill_price.toFixed(2)}</td></tr>`;
        }).join('');

        return `
          <div class="result-box">
            <h3>Round ${lastRoundResult.round_number} resolved</h3>
            <p>${lastRoundResult.price_before.toFixed(2)} → ${lastRoundResult.price_after.toFixed(2)}</p>
            <div class="scroll-x mt-16">
              <table class="data"><thead><tr><th>Trader</th><th>Action</th><th class="num">Qty</th><th class="num">Fill</th></tr></thead><tbody>${trades}</tbody></table>
            </div>
          </div>
        `;
    }

    async function renderFinal() {
        let results;
        try {
            results = await apiCall(`/games/market/${gameId}/results`);
        } catch (e) {
            el.innerHTML = `<div class="state-msg error">Could not load results: ${escapeHTML(e.message)}</div>`;
            return;
        }
        if (disposed) return;

        const rows = results.scores.map((s, i) => `
          <tr${s.player_id === state.currentPlayer.id ? ' class="you"' : ''}>
            <td class="num">${i + 1}</td>
            <td>${escapeHTML(s.player_name)}${s.player_id === state.currentPlayer.id ? ' (you)' : ''}</td>
            <td class="num">${s.score.toFixed(2)}</td>
          </tr>
        `).join('');

        el.innerHTML = `
          <div class="section-head"><h2>Hidden Market — final results</h2></div>
          <div class="box pad">
            <table class="data"><thead><tr><th class="num">Rank</th><th>Trader</th><th class="num">Score</th></tr></thead><tbody>${rows}</tbody></table>
            <p class="mt-24 text-mono text-dim" style="font-size:12px">Price history: ${results.price_history.map(p => p.toFixed(2)).join(' → ')}</p>
          </div>
          <button id="leaveGameBtn" class="btn-danger mt-24">Back to games</button>
        `;
        document.getElementById('leaveGameBtn').addEventListener('click', async () => {
            setRoomCode(null);
            navigate('/');
        });
    }

    function wire(affordable) {
        el.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', () => {
                selectedAction = btn.dataset.action;
                qty = Math.max(1, Math.min(qty, selectedAction === 'SELL' ? Math.max(view.inventory, 1) : affordable || 1));
                render();
            });
        });

        const qtyInput = document.getElementById('qtyInput');
        if (qtyInput) {
            document.getElementById('qtyDown')?.addEventListener('click', () => { qty = Math.max(1, qty - 1); qtyInput.value = qty; });
            document.getElementById('qtyUp')?.addEventListener('click', () => { qty = qty + 1; qtyInput.value = qty; });
            qtyInput.addEventListener('change', () => { qty = Math.max(1, parseInt(qtyInput.value, 10) || 1); });
        }

        document.getElementById('submitAction')?.addEventListener('click', async () => {
            try {
                await apiCall(`/games/market/${gameId}/submit`, 'POST', {
                    player_id: state.currentPlayer.id,
                    action_type: selectedAction,
                    qty: selectedAction === 'HOLD' ? 0 : qty,
                });
                showNotification('Order submitted', 'success');
                await refreshView();
                if (!disposed) render();
            } catch (error) {
                showNotification(error.message, 'error');
            }
        });

        document.getElementById('resolveRoundBtn')?.addEventListener('click', async () => {
            resolving = true;
            render();
            const start = performance.now();
            try {
                const result = await apiCall(`/games/market/${gameId}/resolve`, 'POST');
                lastResolveMs = Math.round(performance.now() - start);
                lastRoundResult = result;
                pushRoundLog(result);
                await refreshView();
            } catch (error) {
                showNotification(error.message, 'error');
            } finally {
                resolving = false;
                if (!disposed) render();
            }
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
        if (data.event === 'market_submission') {
            if (view) { view.submissions_count = data.submissions_count; view.total_players = data.total_players; }
            render();
        } else if (data.event === 'market_round_resolved') {
            lastRoundResult = { round_number: data.round_number, price_before: data.price_before, price_after: data.price_after, trades: data.trades };
            pushRoundLog(lastRoundResult);
            refreshView().then(() => { if (!disposed) render(); });
        } else if (data.event === 'market_game_finished') {
            refreshView().then(() => { if (!disposed) render(); });
        }
    });

    await refreshView();
    if (!disposed) render();

    return () => {
        disposed = true;
        unsubGame();
        disconnectGame();
    };
}
