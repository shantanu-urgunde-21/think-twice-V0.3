// shared.js - Shared utilities and state for the Game Theory Platform

const API_URL = (() => {
    if (window.BACKEND_URL) return window.BACKEND_URL;
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://127.0.0.1:8000/api';
    }
    if (window.location.port === '3000') {
        return '/api';
    }
    return 'https://think-twice-v03-production.up.railway.app/api';
})();

function escapeHTML(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

let currentPlayer = null;
let currentGameId = null;
let adminToken = localStorage.getItem('adminToken');
let isAdmin = false;

async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
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

function backToHome() {
    window.location.href = "index.html";
}

// Admin Authentication logic
function showAdminLogin() {
    const modal = document.getElementById('adminLoginModal');
    if (modal) modal.style.display = 'block';
    const errorEl = document.getElementById('adminLoginError');
    if (errorEl) errorEl.style.display = 'none';
}

function closeAdminLogin() {
    const modal = document.getElementById('adminLoginModal');
    if (modal) modal.style.display = 'none';
    const userEl = document.getElementById('adminUsername');
    if (userEl) userEl.value = '';
    const passEl = document.getElementById('adminPassword');
    if (passEl) passEl.value = '';
    const errorEl = document.getElementById('adminLoginError');
    if (errorEl) errorEl.style.display = 'none';
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
        
        if (typeof updateAdminUI === 'function') updateAdminUI();
        closeAdminLogin();
        showNotification('Admin login successful!', 'success');
    } catch (error) {
        const errorEl = document.getElementById('adminLoginError');
        if (errorEl) {
            errorEl.textContent = error.message;
            errorEl.style.display = 'block';
        }
    }
}

function logoutAdmin() {
    adminToken = null;
    isAdmin = false;
    localStorage.removeItem('adminToken');
    if (typeof updateAdminUI === 'function') updateAdminUI();
    showNotification('Logged out successfully', 'info');
}

async function checkAdminStatus() {
    if (!adminToken) {
        if (typeof updateAdminUI === 'function') updateAdminUI();
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
    
    if (typeof updateAdminUI === 'function') updateAdminUI();
}
