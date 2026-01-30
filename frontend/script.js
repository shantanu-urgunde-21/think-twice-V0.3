// API URL - automatically detects localhost vs production
// For production: If your backend is on a different domain (e.g., Railway),
// set window.BACKEND_URL before this script loads, or update this line directly
const API_URL = (() => {
    // Allow manual override via window.BACKEND_URL
    if (window.BACKEND_URL) {
        return window.BACKEND_URL;
    }
    // Local development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:8000/api';
    }
    // Production: assumes backend is on same domain (if using proxy)
    // Otherwise, you'll need to set window.BACKEND_URL = 'https://your-backend.railway.app/api'
    return 'http://think-twice-v03-production.up.railway.app/api';
    // return `${window.location.protocol}//${window.location.hostname}/api`;
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

    // Set up event listeners
    document.getElementById('registerForm').addEventListener('submit', registerPlayer);
    document.getElementById('twoThirdsForm').addEventListener('submit', submitTwoThirdsGuess);
    
    // Admin login form listener
    const adminLoginForm = document.getElementById('adminLoginForm');
    if (adminLoginForm) {
        adminLoginForm.addEventListener('submit', handleAdminLogin);
    }
    
    // Fish pond form listener
    const fishPondForm = document.getElementById('fishPondForm');
    if (fishPondForm) {
        fishPondForm.addEventListener('submit', submitFishCatch);
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
    backToMenu();
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

// Game Selection
function startGame(gameType) {
    if (!currentPlayer) {
        alert('Please register or select a player first!');
        return;
    }

    if (gameType === 'two-thirds') {
        startTwoThirdsGame();
    } else if (gameType === 'horse-race') {
        startHorseRaceGame();
    } else if (gameType === 'fish-pond') {
        startFishPondGame();
    }
}

function backToHome() {
    // Hide all game views
    document.getElementById('twoThirdsGame').style.display = 'none';
    document.getElementById('horseRaceGame').style.display = 'none';
    document.getElementById('fishPondGame').style.display = 'none';
    
    // Show home view
    document.getElementById('homeView').style.display = 'block';
    document.getElementById('gameSelection').style.display = 'block';
    document.getElementById('leaderboard').style.display = 'block';
    
    currentGameId = null;
    loadLeaderboard();
}

// Legacy function for compatibility
function backToMenu() {
    backToHome();
}

// Two-Thirds Game
async function startTwoThirdsGame() {
    try {
        // Try to get active game first
        let game;
        try {
            game = await apiCall('/games/two-thirds/active');
        } catch {
            // No active game, start new one
            game = await apiCall('/games/two-thirds/start', 'POST');
        }

        currentGameId = game.id;
        document.getElementById('gameSelection').style.display = 'none';
        document.getElementById('twoThirdsGame').style.display = 'block';
        // Hide leaderboard when game starts
        document.getElementById('leaderboard').style.display = 'none';

        // Check if player already submitted
        checkTwoThirdsStatus();
    } catch (error) {
        alert(error.message);
    }
}

async function checkTwoThirdsStatus() {
    try {
        const round = await apiCall(`/games/two-thirds/${currentGameId}/current-round`);
        document.getElementById('submissionCount').textContent = round.submissions_count;
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

async function submitTwoThirdsGuess(e) {
    e.preventDefault();
    const guess = parseInt(document.getElementById('twoThirdsGuess').value);

    try {
        await apiCall(`/games/two-thirds/${currentGameId}/submit`, 'POST', {
            player_id: currentPlayer.id,
            guess: guess
        });

        document.getElementById('twoThirdsForm').style.display = 'none';
        document.getElementById('twoThirdsWaiting').style.display = 'block';
        checkTwoThirdsStatus();
        alert('Guess submitted successfully!');
    } catch (error) {
        alert(error.message);
    }
}

async function calculateTwoThirds() {
    try {
        const result = await apiCall(`/games/two-thirds/${currentGameId}/calculate`, 'POST');

        let html = `<div class="result-box">
            <h3>Results</h3>
            <p><strong>Average:</strong> ${result.average.toFixed(2)}</p>
            <p><strong>2/3 of Average:</strong> ${result.two_thirds_average.toFixed(2)}</p>
            <p class="success"><strong>Winner:</strong> ${result.winner_name}</p>
            <h4>All Guesses:</h4>
            <table class="leaderboard-table">
                <thead><tr><th>Player</th><th>Guess</th><th>Distance</th></tr></thead>
                <tbody>`;

        result.all_guesses.forEach(g => {
            html += `<tr>
                <td>${g.player_name}</td>
                <td>${g.guess}</td>
                <td>${g.distance.toFixed(2)}</td>
            </tr>`;
        });

        html += '</tbody></table></div>';

        document.getElementById('twoThirdsResults').innerHTML = html;
        document.getElementById('twoThirdsResults').style.display = 'block';
        document.getElementById('twoThirdsWaiting').style.display = 'none';

        loadLeaderboard();
        loadStats();
    } catch (error) {
        alert(error.message);
    }
}

// Horse Race Game
async function startHorseRaceGame() {
    try {
        const result = await apiCall('/games/horse-race/start', 'POST', {
            player_id: currentPlayer.id
        });

        currentGameId = result.game_id;
        document.getElementById('gameSelection').style.display = 'none';
        document.getElementById('horseRaceGame').style.display = 'block';
        // Hide leaderboard when game starts
        document.getElementById('leaderboard').style.display = 'none';

        // Load horses
        await loadHorses();
    } catch (error) {
        alert(error.message);
    }
}

async function loadHorses() {
    try {
        allHorses = await apiCall(`/games/horse-race/${currentGameId}/horses`);
        renderHorses();
        populateTopThreeSelects();
    } catch (error) {
        alert(error.message);
    }
}

function renderHorses() {
    const horseList = document.getElementById('horseList');
    horseList.innerHTML = '';

    allHorses.forEach(horse => {
        const div = document.createElement('div');
        div.className = 'horse-item';
        div.textContent = horse.name;
        div.onclick = () => toggleHorse(horse.id, div);
        horseList.appendChild(div);
    });
}

function toggleHorse(horseId, element) {
    if (selectedHorses.includes(horseId)) {
        selectedHorses = selectedHorses.filter(id => id !== horseId);
        element.classList.remove('selected');
    } else if (selectedHorses.length < 5) {
        selectedHorses.push(horseId);
        element.classList.add('selected');
    } else {
        alert('You can only select 5 horses!');
    }

    document.getElementById('raceBtn').disabled = selectedHorses.length !== 5;
}

async function raceSelectedHorses() {
    try {
        const result = await apiCall(`/games/horse-race/${currentGameId}/race`, 'POST', {
            player_id: currentPlayer.id,
            selected_horse_ids: selectedHorses
        });

        document.getElementById('currentRound').textContent = result.round_number;

        let html = '<ol>';
        result.race_results.forEach((horse, idx) => {
            html += `<li>${horse.name}</li>`;
        });
        html += '</ol>';
        html += `<p class="success">${result.message}</p>`;

        document.getElementById('resultsDisplay').innerHTML = html;
        document.getElementById('horseSelection').style.display = 'none';
        document.getElementById('raceResults').style.display = 'block';
    } catch (error) {
        alert(error.message);
    }
}

function nextRound() {
    selectedHorses = [];
    document.getElementById('horseSelection').style.display = 'block';
    document.getElementById('raceResults').style.display = 'none';
    renderHorses();
}

function populateTopThreeSelects() {
    ['first', 'second', 'third'].forEach(id => {
        const select = document.getElementById(id);
        select.innerHTML = '<option value="">Select...</option>';
        allHorses.forEach(horse => {
            const option = document.createElement('option');
            option.value = horse.id;
            option.textContent = horse.name;
            select.appendChild(option);
        });
    });
}

async function submitTopThree() {
    const first = parseInt(document.getElementById('first').value);
    const second = parseInt(document.getElementById('second').value);
    const third = parseInt(document.getElementById('third').value);

    if (!first || !second || !third) {
        alert('Please select all three horses!');
        return;
    }

    if (new Set([first, second, third]).size !== 3) {
        alert('Please select three different horses!');
        return;
    }

    try {
        const result = await apiCall(`/games/horse-race/${currentGameId}/submit-top-three`, 'POST', {
            player_id: currentPlayer.id,
            top_three_ids: [first, second, third]
        });

        let html = '<div class="result-box">';
        if (result.correct) {
            html += `<h3 class="success">Correct! 🎉</h3>
                     <p>You earned ${result.score} points!</p>
                     <p>Rounds used: ${result.rounds_used}</p>`;
        } else {
            html += `<h3 class="error">Incorrect</h3>
                     <p>${result.message}</p>
                     <p>Keep racing to figure it out!</p>`;
        }
        html += '</div>';

        document.getElementById('horseRaceFinalResults').innerHTML = html;
        document.getElementById('horseRaceFinalResults').style.display = 'block';

        if (result.correct) {
            document.getElementById('horseSelection').style.display = 'none';
            document.getElementById('finalSubmission').style.display = 'none';
            loadLeaderboard();
        }
    } catch (error) {
        alert(error.message);
    }
}

// Fish Pond Game
let fishPondGameId = null;

async function startFishPondGame() {
    try {
        const result = await apiCall('/games/fish-pond/start', 'POST');

        fishPondGameId = result.game_id;
        currentGameId = result.game_id;

        document.getElementById('gameSelection').style.display = 'none';
        document.getElementById('fishPondGame').style.display = 'block';
        // Hide leaderboard when game starts
        document.getElementById('leaderboard').style.display = 'none';

        // Initialize UI
        document.getElementById('fpRoundNumber').textContent = '1';
        document.getElementById('fpStockAmount').textContent = '100';
        document.getElementById('fpTotalPlayers').textContent = result.players;

        // Set up form submission
        document.getElementById('fishPondForm').addEventListener('submit', submitFishCatch);

        // Check round status
        updateFishPondRoundStatus();
    } catch (error) {
        alert(error.message);
    }
}

async function updateFishPondRoundStatus() {
    try {
        const status = await apiCall(`/games/fish-pond/${fishPondGameId}/round`);

        document.getElementById('fpRoundNumber').textContent = status.round_number;
        document.getElementById('fpStockAmount').textContent = status.current_stock;
        document.getElementById('fpSubmittedCount').textContent = status.submitted_count;
        document.getElementById('fpTotalPlayers').textContent = status.total_players;

        // Update pending players
        if (status.pending_players.length > 0) {
            const pendingNames = status.pending_players.map(p => p.name).join(', ');
            document.getElementById('pendingPlayers').textContent = `Waiting for: ${pendingNames}`;
            document.getElementById('fishPondInput').style.display = 'block';
            document.getElementById('fishPondWaiting').style.display = 'none';
        } else if (status.submitted_count > 0) {
            document.getElementById('fishPondInput').style.display = 'none';
            document.getElementById('fishPondWaiting').style.display = 'block';
        }
    } catch (error) {
        console.error('Error updating Fish Pond status:', error);
    }
}

async function submitFishCatch(e) {
    e.preventDefault();
    const catchAmount = parseInt(document.getElementById('fpCatchAmount').value);

    try {
        await apiCall(`/games/fish-pond/${fishPondGameId}/submit`, 'POST', {
            player_id: currentPlayer.id,
            catch_amount: catchAmount
        });

        document.getElementById('fishPondForm').reset();
        document.getElementById('fishPondInput').style.display = 'none';
        document.getElementById('fishPondWaiting').style.display = 'block';
        alert('Catch submitted successfully! Waiting for other players...');

        // Refresh status
        updateFishPondRoundStatus();
    } catch (error) {
        alert(error.message);
    }
}

async function calculateFishPondRound() {
    try {
        const result = await apiCall(`/games/fish-pond/${fishPondGameId}/calculate-round`, 'POST');

        let html = `<div class="result-box">
            <h4>Round ${result.round_number} Results</h4>
            <p><strong>Total Catch:</strong> ${result.total_catch} fish</p>
            <p><strong>Stock Remaining:</strong> ${result.stock_at_end} fish</p>`;

        if (result.collapsed) {
            html += `<p class="error"><strong>⚠️ THE POND HAS COLLAPSED! GAME OVER!</strong></p>`;
        } else {
            html += `<p class="success">The pond regenerated and now has ${result.stock_at_end} fish.</p>`;
        }

        html += '<h5>Individual Catches:</h5><table class="leaderboard-table"><thead><tr><th>Player</th><th>Catch</th><th>Score</th></tr></thead><tbody>';

        result.decisions.forEach(d => {
            html += `<tr>
                <td>${d.player_name}</td>
                <td>${d.catch}</td>
                <td>${d.score}</td>
            </tr>`;
        });

        html += '</tbody></table></div>';

        document.getElementById('roundResultsDisplay').innerHTML = html;
        document.getElementById('fishPondWaiting').style.display = 'none';
        document.getElementById('fishPondRoundResults').style.display = 'block';

        if (result.game_ended) {
            setTimeout(() => showFishPondFinalResults(), 2000);
        }
    } catch (error) {
        alert(error.message);
    }
}

async function nextFishPondRound() {
    document.getElementById('fishPondRoundResults').style.display = 'none';
    document.getElementById('fishPondInput').style.display = 'block';
    document.getElementById('fpCatchAmount').value = '';

    updateFishPondRoundStatus();
}

async function showFishPondFinalResults() {
    try {
        const results = await apiCall(`/games/fish-pond/${fishPondGameId}/results`);

        let html = `<div class="result-box">
            <h3>Game Over!</h3>`;

        if (results.game_collapsed) {
            html += `<p class="error">The pond collapsed due to overfishing!</p>`;
        } else {
            html += `<p class="success">Game completed! All rounds finished.</p>`;
        }

        html += '<h4>Final Scores (Total Catch):</h4><table class="leaderboard-table"><thead><tr><th>Rank</th><th>Player</th><th>Total Catch</th></tr></thead><tbody>';

        results.final_scores.forEach((score, idx) => {
            html += `<tr>
                <td>#${idx + 1}</td>
                <td>${score.player_name}</td>
                <td>${score.total_catch}</td>
            </tr>`;
        });

        html += '</tbody></table>';
        html += '<h4>Round Summary:</h4><table class="leaderboard-table"><thead><tr><th>Round</th><th>Start Stock</th><th>Total Catch</th><th>End Stock</th><th>Collapsed</th></tr></thead><tbody>';

        results.all_rounds.forEach(r => {
            html += `<tr>
                <td>${r.round_number}</td>
                <td>${r.stock_at_start}</td>
                <td>${r.total_catch}</td>
                <td>${r.stock_at_end}</td>
                <td>${r.collapsed ? '❌' : '✓'}</td>
            </tr>`;
        });

        html += '</tbody></table></div>';

        document.getElementById('finalResultsDisplay').innerHTML = html;
        document.getElementById('fishPondRoundResults').style.display = 'none';
        document.getElementById('fishPondGameOver').style.display = 'block';

        loadLeaderboard();
        loadStats();
    } catch (error) {
        alert(error.message);
    }
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

async function startFishPondGameAdmin() {
    if (!isAdmin) {
        showNotification('Admin access required', 'error');
        return;
    }
    
    try {
        const response = await apiCall('/games/fish-pond/start', 'POST');
        showNotification('Fish Pond game started successfully!', 'success');
        console.log('Fish Pond game started:', response);
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
