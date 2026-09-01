// main.js — boots the shell, registers routes, opens the lobby socket.

import { renderShell } from './shell.js';
import { route, setNotFound, startRouter, navigate } from './router.js';
import { connectLobby } from './socket.js';
import { state, setPlayer } from './store.js';
import { renderHome } from './views/home.js';
import { renderMarket } from './views/market.js';
import { renderTwoThirds } from './views/twoThirds.js';
import { renderFishPond } from './views/fishPond.js';
import { renderHorseRace } from './views/horseRace.js';

// currentPlayer is loaded synchronously from localStorage by store.js at
// import time; nothing to await here.
if (state.currentPlayer) setPlayer(state.currentPlayer);

renderShell(document.body);

route('/', renderHome);
route('/market', renderMarket);
route('/two-thirds', renderTwoThirds);
route('/fish-pond', renderFishPond);
route('/horse-race', renderHorseRace);

// Shareable room links (/r/F3B8): hand off to the home view, which knows how
// to join a room once a player is logged in.
route('/r/:code', (el, params) => renderHome(el, { joinCode: params.code.toUpperCase() }));

setNotFound((el) => {
    el.innerHTML = `<div class="state-msg">Page not found. <a href="/" class="text-amber">Back to games</a>.</div>`;
});

connectLobby();
startRouter();
