let currentRoomCode = null;
let isLobbyReady = false;
let selectedHorses = [];
let allHorses = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check admin status first
    checkAdminStatus();
    
    // Restore player from localStorage if available
    const savedPlayer = localStorage.getItem('currentPlayer');
    if (savedPlayer) {
        try {
            currentPlayer = JSON.parse(savedPlayer);
            showPlayerLoggedIn();
            
            // Check if player has any active game running
            checkActiveGameAndRedirect();
            
            // Check if we were in a room lobby
            const savedRoom = localStorage.getItem('currentRoomCode');
            if (savedRoom) {
                currentRoomCode = savedRoom;
                loadRoomDetails(savedRoom);
            }
        } catch (e) {
            console.error('Error restoring player from localStorage:', e);
            localStorage.removeItem('currentPlayer');
        }
    }

    loadStats();
    loadLeaderboard();
    loadPlayers();
    loadGameSettings();
    connectLobbyWebSocket();

    // Set up event listeners
    document.getElementById('registerForm').addEventListener('submit', registerPlayer);
    
    // Admin login form listener
    const adminLoginForm = document.getElementById('adminLoginForm');
    if (adminLoginForm) {
        adminLoginForm.addEventListener('submit', handleAdminLogin);
    }
});


// Stats
async function loadStats() {
    try {
        const stats = await apiCall('/stats');
        const playerCountEl = document.getElementById('playerCount');
        const activeGamesEl = document.getElementById('activeGames');
        if (playerCountEl) playerCountEl.textContent = `${stats.total_players}/${stats.max_players}`;
        if (activeGamesEl) activeGamesEl.textContent = stats.active_games;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Players
async function loadPlayers() {
    try {
        const players = await apiCall('/players');
        const select = document.getElementById('existingPlayers');
        select.innerHTML = '<option value="">Choose player...</option>';

        players.forEach(player => {
            const option = document.createElement('option');
            option.value = player.id;
            option.textContent = player.name;
            select.appendChild(option);
        });

        if (players.length > 0) {
            document.getElementById('playerSelect').style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading players:', error);
    }
}

async function registerPlayer(e) {
    e.preventDefault();
    const name = document.getElementById('playerName').value.trim();
    const passcodeVal = document.getElementById('playerRegisterPasscode').value.trim();

    const payload = { name };
    if (passcodeVal) {
        payload.passcode = passcodeVal;
    }

    try {
        const player = await apiCall('/players', 'POST', payload);
        currentPlayer = player;
        
        // Show PIN to player
        const pinDisplay = document.getElementById('generatedPasscode');
        const pinBox = document.getElementById('passcodeDisplayBox');
        if (pinDisplay && pinBox) {
            pinDisplay.textContent = player.passcode;
            pinBox.style.display = 'block';
        }
        
        showPlayerLoggedIn();
        document.getElementById('playerName').value = '';
        document.getElementById('playerRegisterPasscode').value = '';
        loadStats();
        loadPlayers();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function selectPlayer() {
    const select = document.getElementById('existingPlayers');
    if (!select || !select.value) return;

    const playerName = select.options[select.selectedIndex].text;
    const passcode = document.getElementById('playerPasscode').value.trim();

    if (!passcode) {
        showNotification('Please enter your passcode PIN!', 'error');
        return;
    }

    apiCall('/players/verify', 'POST', { name: playerName, passcode })
        .then(player => {
            currentPlayer = player;
            showPlayerLoggedIn();
            document.getElementById('playerPasscode').value = '';
            
            // Hide the passcode display box if it was open
            const pinBox = document.getElementById('passcodeDisplayBox');
            if (pinBox) pinBox.style.display = 'none';
        })
        .catch(error => showNotification(error.message, 'error'));
}

function showPlayerLoggedIn() {
    // Save to localStorage
    if (currentPlayer) {
        localStorage.setItem('currentPlayer', JSON.stringify(currentPlayer));
    }

    const regFields = document.getElementById('registrationFields');
    if (regFields) regFields.style.display = 'none';
    
    const registrationHeader = document.querySelector('#registration h2');
    if (registrationHeader) registrationHeader.innerHTML = '👤 Your Profile';

    document.getElementById('currentPlayer').style.display = 'block';
    document.getElementById('currentPlayerName').textContent = currentPlayer.name;
    
    const pinElLocal = document.getElementById('currentPlayerPIN');
    if (pinElLocal) pinElLocal.textContent = currentPlayer.passcode;
    
    // Update header badge
    const badge = document.getElementById('playerBadge');
    const nameEl = document.getElementById('playerDisplayName');
    const pinEl = document.getElementById('playerDisplayPIN');
    const logoutBtn = document.getElementById('logoutPlayerBtn');
    if (badge) badge.style.display = 'inline-flex';
    if (nameEl) nameEl.textContent = currentPlayer.name;
    if (pinEl) pinEl.textContent = 'PIN: ' + currentPlayer.passcode;
    if (logoutBtn) logoutBtn.style.display = 'inline-block';

    document.getElementById('gameSelection').style.display = 'block';
    // Keep leaderboard visible
    document.getElementById('leaderboard').style.display = 'block';
}

function logout() {
    // Clear localStorage
    localStorage.removeItem('currentPlayer');
    currentPlayer = null;
    
    // Hide passcode display box if visible
    const pinBox = document.getElementById('passcodeDisplayBox');
    if (pinBox) pinBox.style.display = 'none';
    
    // Update header badge
    const badge = document.getElementById('playerBadge');
    const logoutBtn = document.getElementById('logoutPlayerBtn');
    if (badge) badge.style.display = 'none';
    if (logoutBtn) logoutBtn.style.display = 'none';
    
    const regFields = document.getElementById('registrationFields');
    if (regFields) regFields.style.display = 'block';
    
    const registrationHeader = document.querySelector('#registration h2');
    if (registrationHeader) registrationHeader.innerHTML = 'Player Registration';
    
    document.getElementById('currentPlayer').style.display = 'none';
    document.getElementById('gameSelection').style.display = 'none';
    backToHome();
}

// Leaderboard
async function loadLeaderboard() {
    try {
        const leaderboard = await apiCall('/leaderboard');
        const content = document.getElementById('leaderboardContent');

        if (leaderboard.length === 0) {
            content.innerHTML = '<p>No players yet.</p>';
            return;
        }

        let html = '<table class="leaderboard-table"><thead><tr><th>Rank</th><th>Player</th><th>Score</th></tr></thead><tbody>';

        leaderboard.forEach(entry => {
            const rankClass = entry.rank <= 3 ? `rank-${entry.rank}` : '';
            html += `<tr class="${rankClass}">
                <td>#${entry.rank}</td>
                <td>${escapeHTML(entry.player_name)}</td>
                <td>${entry.total_score}</td>
            </tr>`;
        });

        html += '</tbody></table>';
        content.innerHTML = html;
    } catch (error) {
        console.error('Error loading leaderboard:', error);
    }
}

// Game Settings
async function loadGameSettings() {
    try {
        const enabledGames = await apiCall('/games/enabled');
        const gameButtons = document.querySelectorAll('.game-buttons a');
        
        // Build a set of enabled game names
        const enabledGameNames = new Set(enabledGames.map(g => g.game_name));
        
        // Hide/show game buttons based on enabled status
        gameButtons.forEach(button => {
            const href = button.getAttribute('href');
            let gameName = '';
            
            if (href.includes('two-thirds')) {
                gameName = 'two_thirds';
            } else if (href.includes('horse-race')) {
                gameName = 'horse_race';
            } else if (href.includes('fish-pond')) {
                gameName = 'fish_pond';
            }
            
            if (gameName && !enabledGameNames.has(gameName)) {
                button.style.display = 'none';
            } else {
                button.style.display = 'block';
            }
        });
    } catch (error) {
        console.error('Error loading game settings:', error);
    }
}

async function loadAdminGameSettings() {
    try {
        const settings = await apiCall('/games/settings');
        const panel = document.getElementById('gameSettingsPanel');
        
        let html = '<div class="game-settings">';
        settings.forEach(setting => {
            const displayName = {
                'two_thirds': '2/3 of Average',
                'horse_race': 'Horse Racing',
                'fish_pond': 'Fish Pond'
            }[setting.game_name] || setting.game_name;
            html += `<div class="setting-row">
                <label>${displayName}</label>
                <input type="checkbox" ${setting.enabled ? 'checked' : ''} 
                       onchange="toggleGameVisibility('${setting.game_name}', this.checked)">
                <span>${setting.enabled ? 'Enabled' : 'Disabled'}</span>
            </div>`;
        });
        html += '</div>';
        
        panel.innerHTML = html;
    } catch (error) {
        console.error('Error loading admin game settings:', error);
    }
}

async function toggleGameVisibility(gameName, enabled) {
    try {
        await apiCall(`/games/settings/${gameName}`, 'PUT', {
            game_name: gameName,
            enabled: enabled
        });
        
        showNotification(`${gameName.replace('_', ' ')} visibility updated`, 'success');
        loadGameSettings(); // Reload settings on homepage
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

// Game Selection - Games are now on separate pages
// The game buttons are links, so no need for startGame function anymore

function backToHome() {
    // Show home view
    document.getElementById('homeView').style.display = 'block';
    document.getElementById('gameSelection').style.display = 'block';
    document.getElementById('leaderboard').style.display = 'block';
    
    currentGameId = null;
    loadLeaderboard();
}


function updateAdminUI() {
    const loginBtn = document.getElementById('adminLoginBtn');
    const logoutBtn = document.getElementById('adminLogoutBtn');
    const adminPanel = document.getElementById('adminPanel');
    const adminBadge = document.getElementById('adminBadge');
    
    if (loginBtn) loginBtn.style.display = isAdmin ? 'none' : 'block';
    if (logoutBtn) logoutBtn.style.display = isAdmin ? 'block' : 'none';
    if (adminPanel) adminPanel.style.display = isAdmin ? 'block' : 'none';
    if (adminBadge) adminBadge.style.display = isAdmin ? 'inline-flex' : 'none';
    
    // Show/hide admin action buttons
    document.querySelectorAll('.admin-action').forEach(btn => {
        btn.style.display = isAdmin ? 'block' : 'none';
    });
    
    // Load admin settings if admin
    if (isAdmin) {
        loadAdminGameSettings();
        loadAdminPlayerManagement();
    }
}

async function loadAdminPlayerManagement() {
    try {
        const players = await apiCall('/players');
        const panel = document.getElementById('playerManagement');
        if (!panel) return;
        
        if (players.length === 0) {
            panel.innerHTML = '<p>No players registered yet.</p>';
            return;
        }
        
        let html = `
            <table class="leaderboard-table" style="margin-top: 10px;">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>PIN</th>
                        <th>Score</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        players.forEach(p => {
            html += `
                <tr>
                    <td>${escapeHTML(p.name)}</td>
                    <td><strong style="color: #ffb700;">${p.passcode || 'N/A'}</strong></td>
                    <td>${p.total_score}</td>
                    <td>
                        <button onclick="deletePlayerAdmin(${p.id}, '${escapeHTML(p.name.replace(/'/g, "\\'"))}')" 
                                style="padding: 4px 8px; font-size: 0.75rem; background-color: var(--color-accent-rust); margin: 0; min-height: auto; width: auto;">
                            Delete
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += `
                </tbody>
            </table>
            <div style="display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap;">
                <button onclick="resetScoresAdmin()" class="admin-btn" style="font-size: 0.8rem; padding: 8px 16px; background-color: #4a3b32;">
                    Reset All Scores
                </button>
                <button onclick="clearAllPlayersAdmin()" class="admin-btn" style="font-size: 0.8rem; padding: 8px 16px; background-color: var(--color-accent-rust);">
                    Delete All Players
                </button>
            </div>
        `;
        panel.innerHTML = html;
    } catch (error) {
        console.error('Error loading admin player management:', error);
    }
}

async function deletePlayerAdmin(id, name) {
    if (!confirm(`Are you sure you want to delete player "${name}"?`)) return;
    try {
        await apiCall(`/players/${id}`, 'DELETE');
        showNotification(`Player "${name}" deleted`, 'success');
        loadAdminPlayerManagement();
        loadLeaderboard();
        loadPlayers();
        loadStats();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function resetScoresAdmin() {
    if (!confirm('Are you sure you want to reset all players\' scores to 0?')) return;
    try {
        await apiCall('/players/reset-scores', 'POST');
        showNotification('All player scores have been reset', 'success');
        loadAdminPlayerManagement();
        loadLeaderboard();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function clearAllPlayersAdmin() {
    if (!confirm('WARNING: Are you absolutely sure you want to delete ALL players? This cannot be undone.')) return;
    try {
        await apiCall('/players/clear-all', 'POST');
        showNotification('All players deleted', 'success');
        loadAdminPlayerManagement();
        loadLeaderboard();
        loadPlayers();
        loadStats();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function startFishPondGameAdmin() {
    if (!isAdmin) {
        showNotification('Admin access required', 'error');
        return;
    }
    try {
        await apiCall('/games/fish-pond/start', 'POST');
        showNotification('Fish Pond game started successfully!', 'success');
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

// ==================== ADMIN GAME MANAGEMENT ====================

async function startTwoThirdsGameAdmin() {
    if (!isAdmin) {
        showNotification('Admin access required', 'error');
        return;
    }
    
    try {
        await apiCall('/games/two-thirds/start', 'POST');
        showNotification('Two-Thirds game started successfully!', 'success');
    } catch (error) {
        showNotification(error.message, 'error');
    }
}


// ==================== LOBBY WEBSOCKETS ====================

function connectLobbyWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/lobby`;
    
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.event === 'player_registered') {
                loadStats();
                loadPlayers();
                loadLeaderboard();
            } else if (data.event === 'settings_updated') {
                loadGameSettings();
            } else if (data.event === 'lobby_updated') {
                if (currentRoomCode && data.room_code === currentRoomCode) {
                    loadRoomDetails(currentRoomCode);
                }
            } else if (data.event === 'game_started') {
                if (currentRoomCode && data.room_code === currentRoomCode) {
                    localStorage.removeItem('currentRoomCode');
                    currentRoomCode = null;
                    checkActiveGameAndRedirect();
                } else {
                    showNotification(`Game started: ${data.game_name.replace('_', ' ')}!`, 'success');
                    loadGameSettings();
                }
            }
        } catch (e) {
            console.error('Error handling websocket message:', e);
        }
    };
    ws.onclose = () => {
        // Retry connection in 3 seconds
        setTimeout(connectLobbyWebSocket, 3000);
    };
}

// ==================== ROOMS & LOBBIES MANAGEMENT ====================

async function createLobbyRoom() {
    if (!currentPlayer) {
        showNotification('Please register or log in first!', 'error');
        return;
    }
    const game_name = document.getElementById('lobbyGameSelect').value;
    try {
        const room = await apiCall('/rooms/create', 'POST', {
            player_id: currentPlayer.id,
            game_name
        });
        currentRoomCode = room.room_code;
        localStorage.setItem('currentRoomCode', currentRoomCode);
        isLobbyReady = true; // Host is ready by default
        renderRoomUI(room);
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function joinLobbyRoom() {
    if (!currentPlayer) {
        showNotification('Please register or log in first!', 'error');
        return;
    }
    const room_code = document.getElementById('joinRoomCode').value.trim().toUpperCase();
    if (!room_code) {
        showNotification('Please enter a room code!', 'error');
        return;
    }
    try {
        const room = await apiCall('/rooms/join', 'POST', {
            player_id: currentPlayer.id,
            room_code
        });
        currentRoomCode = room.room_code;
        localStorage.setItem('currentRoomCode', currentRoomCode);
        isLobbyReady = false;
        renderRoomUI(room);
        document.getElementById('joinRoomCode').value = '';
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function loadRoomDetails(roomCode) {
    try {
        const room = await apiCall(`/rooms/${roomCode}`);
        
        // If the game status is active, redirect to the game
        if (room.status === 'active') {
            localStorage.removeItem('currentRoomCode'); // Clear waiting state
            checkActiveGameAndRedirect();
            return;
        }
        
        renderRoomUI(room);
    } catch (error) {
        console.error('Error loading room details:', error);
        // Clean up stale local storage
        localStorage.removeItem('currentRoomCode');
        currentRoomCode = null;
        if (currentPlayer) {
            showPlayerLoggedIn();
        }
    }
}

function renderRoomUI(room) {
    document.getElementById('gameSelection').style.display = 'none';
    document.getElementById('lobbyRoomView').style.display = 'block';
    
    document.getElementById('lobbyRoomCode').textContent = room.room_code;
    
    const displayNames = {
        'two_thirds': '2/3 of Average',
        'fish_pond': 'Fish Pond',
        'horse_race': 'Horse Racing'
    };
    document.getElementById('lobbyRoomGameName').textContent = displayNames[room.game_name] || room.game_name;
    document.getElementById('lobbyRoomHostName').textContent = room.host_name || 'N/A';
    
    // Render members
    const tbody = document.getElementById('lobbyRoomMembers');
    tbody.innerHTML = '';
    
    let allReady = true;
    room.members.forEach(m => {
        const isHost = m.player_id === room.host_id;
        const readyText = m.is_ready ? '✅ READY' : '⏳ WAITING';
        const readyClass = m.is_ready ? 'rank-1' : 'rank-3';
        
        if (!m.is_ready) allReady = false;
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHTML(m.player_name)} ${isHost ? '👑 (Host)' : ''}</td>
            <td class="${readyClass}" style="font-weight: bold;">${readyText}</td>
        `;
        tbody.appendChild(tr);
        
        // Update local ready state if matching current player
        if (m.player_id === currentPlayer.id) {
            isLobbyReady = m.is_ready;
            const readyBtn = document.getElementById('lobbyReadyBtn');
            if (readyBtn) {
                readyBtn.textContent = isLobbyReady ? 'Set Not Ready' : 'Set Ready';
                readyBtn.className = isLobbyReady ? 'back-btn' : 'game-btn';
                readyBtn.style.marginTop = '0';
            }
        }
    });
    
    // Toggle start game button visibility for Host
    const startBtn = document.getElementById('lobbyStartGameBtn');
    if (startBtn) {
        const isHostPlayer = currentPlayer.id === room.host_id;
        startBtn.style.display = isHostPlayer ? 'inline-block' : 'none';
        startBtn.disabled = !allReady || room.members.length < 2;
    }
}

async function toggleLobbyReady() {
    if (!currentRoomCode || !currentPlayer) return;
    try {
        const newReadyState = !isLobbyReady;
        await apiCall(`/rooms/${currentRoomCode}/ready?player_id=${currentPlayer.id}&is_ready=${newReadyState}`, 'POST');
        loadRoomDetails(currentRoomCode);
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function startLobbyGame() {
    if (!currentRoomCode || !currentPlayer) return;
    try {
        await apiCall(`/rooms/${currentRoomCode}/start?host_id=${currentPlayer.id}`, 'POST');
        showNotification('Starting game...', 'success');
        checkActiveGameAndRedirect();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function leaveLobbyRoom() {
    if (!currentRoomCode || !currentPlayer) return;
    try {
        await apiCall(`/rooms/${currentRoomCode}/leave?player_id=${currentPlayer.id}`, 'POST');
        localStorage.removeItem('currentRoomCode');
        currentRoomCode = null;
        
        document.getElementById('lobbyRoomView').style.display = 'none';
        showPlayerLoggedIn();
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function checkActiveGameAndRedirect() {
    if (!currentPlayer) return;
    try {
        const active = await apiCall(`/rooms/active-player-game/${currentPlayer.id}`);
        if (active) {
            const gamePage = {
                'two_thirds': 'two-thirds-game.html',
                'fish_pond': 'fish-pond-game.html',
                'horse_race': 'horse-race-game.html'
            }[active.game_name];
            if (gamePage) {
                showNotification(`Room game is active! Redirecting...`, 'success');
                setTimeout(() => {
                    window.location.href = gamePage;
                }, 1000);
            }
        }
    } catch (e) {
        // Not in active game
    }
}
