// api.js — HTTP client shared by every view.

export const API_URL = (() => {
    if (window.BACKEND_URL) return window.BACKEND_URL;
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://127.0.0.1:8000/api';
    }
    return '/api';
})();

export function escapeHTML(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/[&<>'"]/g,
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;',
        }[tag] || tag)
    );
}

/**
 * @returns {Promise<any>}
 */
export async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };

    const adminToken = localStorage.getItem('adminToken');
    if (adminToken) {
        options.headers['Authorization'] = `Bearer ${adminToken}`;
    }

    if (data) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(`${API_URL}${endpoint}`, options);

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'API call failed');
    }

    return response.json();
}

/** Root origin (no /api suffix) — used for auth endpoints. */
export const ROOT_URL = API_URL.replace(/\/api$/, '');
