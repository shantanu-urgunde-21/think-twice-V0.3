// router.js — tiny History API router. No page reload, no dependency —
// this is what lets the WebSocket in socket.js survive navigation.

const routes = [];
let notFound = null;
let currentDispose = null;
const viewEl = () => document.getElementById('view');

/** @param {string} pattern e.g. '/r/:code' */
export function route(pattern, render) {
    const paramNames = [];
    const regex = new RegExp(
        '^' +
        pattern.replace(/:[^/]+/g, (m) => {
            paramNames.push(m.slice(1));
            return '([^/]+)';
        }) +
        '$'
    );
    routes.push({ regex, paramNames, render });
}

export function setNotFound(render) {
    notFound = render;
}

async function dispatch() {
    const path = window.location.pathname || '/';

    if (typeof currentDispose === 'function') {
        try { currentDispose(); } catch (e) { console.error(e); }
        currentDispose = null;
    }

    for (const r of routes) {
        const match = path.match(r.regex);
        if (match) {
            const params = {};
            r.paramNames.forEach((name, i) => { params[name] = match[i + 1]; });
            const el = viewEl();
            el.innerHTML = '';
            const dispose = await r.render(el, params);
            currentDispose = typeof dispose === 'function' ? dispose : null;
            window.scrollTo(0, 0);
            return;
        }
    }

    if (notFound) {
        const el = viewEl();
        el.innerHTML = '';
        const dispose = await notFound(el);
        currentDispose = typeof dispose === 'function' ? dispose : null;
    }
}

/** Client-side navigation. Falls back to a real navigation for cross-origin hrefs. */
export function navigate(path) {
    if (path === window.location.pathname) {
        dispatch();
        return;
    }
    window.history.pushState({}, '', path);
    dispatch();
}

export function startRouter() {
    window.addEventListener('popstate', dispatch);

    // Intercept same-origin link clicks so navigation never reloads the page.
    document.addEventListener('click', (e) => {
        const link = e.target.closest('a[href]');
        if (!link) return;
        if (link.target === '_blank' || link.hasAttribute('download')) return;
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;

        const url = new URL(link.href, window.location.href);
        if (url.origin !== window.location.origin) return;

        e.preventDefault();
        navigate(url.pathname);
    });

    dispatch();
}

export function currentPath() {
    return window.location.pathname;
}
