let isRefreshing = false;
let failedQueue = [];

function processQueue(error) {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve();
        }
    });
    failedQueue = [];
}

function refreshTokens() {
    return new Promise((resolve, reject) => {
        $.ajax({
            url: '/refresh_access',
            method: 'POST',
            xhrFields: { withCredentials: true }
        })
        .done(resolve)
        .fail(reject);
    });
}

function ajaxWithAuth(options) {
    const request = new Promise((resolve, reject) => {
        $.ajax({
            ...options,
            xhrFields: { withCredentials: true },
            headers: {
                ...options.headers,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .done(resolve)
        .fail(xhr => {
            if (xhr.status !== 401) {
                reject(xhr);
                return;
            }

            if (options.url === '/refresh_access') {
                var next_url = document.URL;
                window.location.href = '/auth/login.html?next=' + next_url;
                reject(xhr);
                return;
            }

            if (isRefreshing) {
                failedQueue.push({ resolve, reject });
                return;
            }

            isRefreshing = true;

            refreshTokens()
                .then(() => {
                    processQueue(null);
                    return $.ajax({
                            ...options,
                            xhrFields: { withCredentials: true },
                            headers: {
                                ...options.headers,
                                'X-Requested-With': 'XMLHttpRequest'
                            }
                         })
                        .done(resolve)
                        .fail(reject);
                })
                .catch(err => {
                    var next_url = document.URL;
                    processQueue(err);
                    window.location.href = '/auth/login.html?next=' + next_url;
                    reject(err);
                })
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

function fetchWithAuth(url, options = {}) {
    const request = new Promise((resolve, reject) => {
        fetch(url, {
            ...options,
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                ...(options.headers || {})
            }
        })
        .then(response => {
            if (response.status !== 401) {
                return response;
            }

            if (isRefreshing) {
                return new Promise((res, rej) => {
                    failedQueue.push({ resolve: res, reject: rej });
                })
                .then(() => fetch(url, options))
                .then(resolve)
                .catch(reject);
            }

            isRefreshing = true;

            return refreshTokens()
                .then(() => {
                    processQueue(null);
                    return fetch(url, {
                       ...options,
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest',
                            ...(options.headers || {})
                        }
                    });
                })
                .then(resolve)
                .catch(err => {
                    processQueue(err);
                    var next_url = document.URL;
                    window.location.href = '/auth/login.html?next=' + next_url;
                    throw err;
                })
                .finally(() => {
                    isRefreshing = false;
                });
        })
        .then(resolve)
        .catch(reject);
    });
    // Same as ajaxWithAuth: avoid Uncaught (in promise) for callers that
    // rely on callbacks and ignore the returned promise.
    request.catch(() => {});
    return request;
}
