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
    return new Promise((resolve, reject) => {
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
}

function fetchWithAuth(url, options = {}) {
    return new Promise((resolve, reject) => {
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
}
