const ExternalUrlFor = function (url, baseUrl = "{{ EXTERNAL_BASE_URL }}") {
    if (/^(https?:)?\/\//i.test(url)) {
        return url;
    }

    if (!baseUrl || baseUrl.trim() === '') {
        return url.startsWith('/') ? url : '/' + url;
    }


    const cleanBase = baseUrl.replace(/\/+$/, '');
    const cleanPath = url.replace(/^\/+/, '');

    return cleanBase + '/' + cleanPath;
};