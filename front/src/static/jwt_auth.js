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
                window.location.href = '/login';
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
                    processQueue(err);
                    window.location.href = '/login';
                    reject(err);
                })
                .finally(() => {
                    isRefreshing = false;
                });
        });
    });
}

