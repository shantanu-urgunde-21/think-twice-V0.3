// API URL - automatically detects localhost vs production
// For production: Backend URL should be set via environment variable
const API_URL = (() => {
    // Allow manual override via window.BACKEND_URL
    if (window.BACKEND_URL) {
        return window.BACKEND_URL;
    }
    // Local development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:8000/api';
    }
    // Production: Use environment variable or Railway backend URL
    // This is a fallback - should be configured via environment variables in Vercel
    return 'https://think-twice-v03-production.up.railway.app/api';
})();

let currentPlayer = null;
let currentGameId = null;
let selectedHorses = [];
let allHorses = [];

// Admin authentication state
let adminToken = localStorage.getItem('adminToken');
let isAdmin = false;

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
        } catch (e) {
            console.error('Error restoring player from localStorage:', e);
            localStorage.removeItem('currentPlayer');
        }
    }

    loadStats();
    loadLeaderboard();
    loadPlayers();
    loadGameSettings();

    // Set up event listeners
    document.getElementById('registerForm').addEventListener('submit', registerPlayer);
    
    // Admin login form listener
    const adminLoginForm = document.getElementById('adminLoginForm');
    if (adminLoginForm) {
        adminLoginForm.addEventListener('submit', handleAdminLogin);
    }
});

// API Calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    // Add authorization header if admin is logged in
    if (adminToken) {
        options.headers['Authorization'] = `Bearer ${adminToken}`;
    }

    if (data) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(`${API_URL}${endpoint}`, options);

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'API call failed');
    }

    return response.json();
}

// Stats
async function loadStats() {
    try {
        const stats = await apiCall('/stats');
        document.getElementById('playerCount').textContent = `${stats.total_players}/${stats.max_players}`;
        document.getElementById('activeGames').textContent = stats.active_games;
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

    try {
        const player = await apiCall('/players', 'POST', { name });
        currentPlayer = player;
        showPlayerLoggedIn();
        document.getElementById('playerName').value = '';
        loadStats();
        loadPlayers();
    } catch (error) {
        alert(error.message);
    }
}

function selectPlayer() {
    const playerId = document.getElementById('existingPlayers').value;
    if (!playerId) return;

    apiCall(`/players/${playerId}`)
        .then(player => {
            currentPlayer = player;
            showPlayerLoggedIn();
        })
        .catch(error => alert(error.message));
}

function showPlayerLoggedIn() {
    // Save to localStorage
    if (currentPlayer) {
        localStorage.setItem('currentPlayer', JSON.stringify(currentPlayer));
    }

    document.getElementById('registration').style.display = 'none';
    document.getElementById('currentPlayer').style.display = 'block';
    document.getElementById('currentPlayerName').textContent = currentPlayer.name;
    document.getElementById('gameSelection').style.display = 'block';
    // Keep leaderboard visible
    document.getElementById('leaderboard').style.display = 'block';
}

function logout() {
    // Clear localStorage
    localStorage.removeItem('currentPlayer');
    currentPlayer = null;
    document.getElementById('registration').style.display = 'block';
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
                <td>${entry.player_name}</td>
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
            const displayName = setting.game_name === 'two_thirds' ? '2/3 of Average' : 'Horse Racing';
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

// ==================== ADMIN AUTHENTICATION ====================

function showAdminLogin() {
    document.getElementById('adminLoginModal').style.display = 'block';
    document.getElementById('adminLoginError').style.display = 'none';
}

function closeAdminLogin() {
    document.getElementById('adminLoginModal').style.display = 'none';
    document.getElementById('adminUsername').value = '';
    document.getElementById('adminPassword').value = '';
    document.getElementById('adminLoginError').style.display = 'none';
}

async function handleAdminLogin(e) {
    e.preventDefault();
    const username = document.getElementById('adminUsername').value;
    const password = document.getElementById('adminPassword').value;
    
    try {
        const response = await fetch(`${API_URL.replace('/api', '')}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            throw new Error('Invalid credentials');
        }
        
        const data = await response.json();
        adminToken = data.access_token;
        localStorage.setItem('adminToken', adminToken);
        isAdmin = true;
        
        updateAdminUI();
        closeAdminLogin();
        showNotification('Admin login successful!', 'success');
    } catch (error) {
        document.getElementById('adminLoginError').textContent = error.message;
        document.getElementById('adminLoginError').style.display = 'block';
    }
}

function logoutAdmin() {
    adminToken = null;
    isAdmin = false;
    localStorage.removeItem('adminToken');
    updateAdminUI();
    showNotification('Logged out successfully', 'info');
}

async function checkAdminStatus() {
    if (!adminToken) {
        updateAdminUI();
        return;
    }
    
    try {
        const response = await fetch(`${API_URL.replace('/api', '')}/api/auth/verify`, {
            headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        
        if (response.ok) {
            isAdmin = true;
        } else {
            logoutAdmin();
            return;
        }
    } catch (error) {
        logoutAdmin();
        return;
    }
    
    updateAdminUI();
}

function updateAdminUI() {
    const loginBtn = document.getElementById('adminLoginBtn');
    const logoutBtn = document.getElementById('adminLogoutBtn');
    const adminPanel = document.getElementById('adminPanel');
    
    if (loginBtn) loginBtn.style.display = isAdmin ? 'none' : 'block';
    if (logoutBtn) logoutBtn.style.display = isAdmin ? 'block' : 'none';
    if (adminPanel) adminPanel.style.display = isAdmin ? 'block' : 'none';
    
    // Show/hide admin action buttons
    document.querySelectorAll('.admin-action').forEach(btn => {
        btn.style.display = isAdmin ? 'block' : 'none';
    });
    
    // Load admin game settings if admin
    if (isAdmin) {
        loadAdminGameSettings();
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

// ==================== NOTIFICATION SYSTEM ====================

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    if (!notification) {
        console.log('Notification:', message);
        return;
    }
    
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// ==================== GAME VIEW MANAGEMENT ====================

function startGame(gameType) {
    if (!currentPlayer) {
        showNotification('Please register or select a player first!', 'error');
        return;
    }
    
    // Hide home view
    document.getElementById('homeView').style.display = 'none';
    
    if (gameType === 'two-thirds') {
        startTwoThirdsGame();
    } else if (gameType === 'horse-race') {
        startHorseRaceGame();
    } else if (gameType === 'fish-pond') {
        startFishPondGame();
    }
}

