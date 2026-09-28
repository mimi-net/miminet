let isRefreshing = false;
let failedQueue = [];

function redirectToLogin() {
    var next_url = document.URL;
    window.location.href = '/auth/login.html?next=' + next_url;
}

function getCookie(name) {
    // csrf_* cookies are readable by design (double-submit pattern, not HttpOnly)
    const match = document.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : null;
}

function isRefreshUrl(url) {
    const tail = String(url || '').split('?')[0];
    return tail === '/refresh_access' || tail.endsWith('/refresh_access');
}

function csrfTokenFor(url) {
    // The refresh endpoint is authorized by the refresh cookie, everything
    // else by the access cookie — flask-jwt-extended expects the matching
    // CSRF token ('csrf_refresh_token' / 'csrf_access_token' by default;
    // coupled with JWT_*_CSRF_COOKIE_NAME in front/src/app.py).
    return getCookie(isRefreshUrl(url) ? 'csrf_refresh_token' : 'csrf_access_token');
}

function isUnsafeMethod(options) {
    const method = String(options.type || options.method || 'GET').toUpperCase();
    return method === 'POST' || method === 'PUT' || method === 'PATCH' || method === 'DELETE';
}

function csrfHeaders(options) {
    // Attach X-CSRF-TOKEN for cookie-JWT writes. Required in prod where
    // JWT_COOKIE_CSRF_PROTECT=True; harmless in dev where it is False.
    // An explicit caller header always wins. The token is re-read on every
    // attempt because refresh rotates cookies.
    if (!isUnsafeMethod(options)) {
        return {};
    }
    const headers = options.headers || {};
    if (headers['X-CSRF-TOKEN']) {
        return {};
    }
    const token = csrfTokenFor(options.url);
    return token ? { 'X-CSRF-TOKEN': token } : {};
}

function baseAjax(options) {
    return $.ajax({
        ...options,
        xhrFields: { withCredentials: true },
        headers: {
            ...options.headers,
            ...csrfHeaders(options),
            'X-Requested-With': 'XMLHttpRequest'
        }
    });
}

function refreshTokens() {
    return new Promise((resolve, reject) => {
        // NOTE: intentionally no X-Requested-With here. Without it the
        // backend treats a dead refresh token as a browser navigation and
        // bounces through /auth/login.html, which mints fresh cookies while
        // the login session is alive — the retry below then succeeds without
        // ever reloading the page. With the header we would get JSON 401 and
        // lose the in-flight edit to a full-page redirect.
        $.ajax({
            url: '/refresh_access',
            method: 'POST',
            xhrFields: { withCredentials: true },
            headers: { ...csrfHeaders({ url: '/refresh_access', method: 'POST' }) }
        })
        .done(resolve)
        .fail(reject);
    });
}

function flushQueue() {
    const queued = failedQueue;
    failedQueue = [];
    return queued;
}

function ajaxWithAuth(options) {
    const request = new Promise((resolve, reject) => {
        baseAjax(options)
        .done(resolve)
        .fail(xhr => {
            if (xhr.status !== 401) {
                reject(xhr);
                return;
            }

            if (isRefreshUrl(options.url)) {
                redirectToLogin();
                reject(xhr);
                return;
            }

            if (isRefreshing) {
                // A refresh is already running: retry after it finishes
                // instead of resolving with `undefined` (issue #550).
                failedQueue.push({
                    retry: () => baseAjax(options).done(resolve).fail(reject),
                    reject
                });
                return;
            }

            isRefreshing = true;

            refreshTokens()
                .then(
                    () => {
                        flushQueue().forEach(item => item.retry());
                        return baseAjax(options);
                    },
                    err => {
                        flushQueue().forEach(item => item.reject(err));
                        redirectToLogin();
                        throw err;
                    }
                )
                .then(resolve, reject)
                .finally(() => {
                    isRefreshing = false;
                });
        });
    });
    // All call sites use legacy jQuery-style success/error callbacks and ignore
    // the returned promise, so an unobserved rejection spams the console with
    // Uncaught (in promise). Mark it handled here; promise-style callers can
    // still observe the rejection via their own .then/.catch chain.
    request.catch(() => {});
    return request;
}

function fetchAttempt(url, options) {
    return fetch(url, {
        ...options,
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            ...(options.headers || {}),
            ...csrfHeaders({ url, method: options.method || 'GET', headers: options.headers })
        }
    });
}

function fetchWithAuth(url, options = {}) {
    const request = new Promise((resolve, reject) => {
        fetchAttempt(url, options)
        .then(response => {
            if (response.status !== 401) {
                resolve(response);
                return;
            }

            if (isRefreshUrl(url)) {
                redirectToLogin();
                reject(response);
                return;
            }

            if (isRefreshing) {
                failedQueue.push({
                    retry: () => fetchAttempt(url, options).then(resolve, reject),
                    reject
                });
                return;
            }

            isRefreshing = true;

            refreshTokens()
                .then(
                    () => {
                        flushQueue().forEach(item => item.retry());
                        return fetchAttempt(url, options);
                    },
                    err => {
                        flushQueue().forEach(item => item.reject(err));
                        redirectToLogin();
                        throw err;
                    }
                )
                .then(resolve, reject)
                .finally(() => {
                    isRefreshing = false;
                });
        })
        .catch(reject);
    });
    // Same as ajaxWithAuth: avoid Uncaught (in promise) for callers that
    // rely on callbacks and ignore the returned promise.
    request.catch(() => {});
    return request;
}
