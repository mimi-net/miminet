"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getVimeoURLParams = exports.param = void 0;
exports.param = function (obj) {
    return Object.keys(obj)
        .map(function (k) {
        return encodeURIComponent(k) + '=' + encodeURIComponent(obj[k]);
    })
        .join('&');
};
exports.getVimeoURLParams = function (defaultParams, videoInfo) {
    if (!videoInfo || !videoInfo.vimeo)
        return '';
    var urlParams = videoInfo.vimeo[2] || '';
    var defaultPlayerParams = defaultParams && Object.keys(defaultParams).length !== 0
        ? '&' + exports.param(defaultParams)
        : '';
    // Support private video
    var urlWithHash = videoInfo.vimeo[0].split('/').pop() || '';
    var urlWithHashWithParams = urlWithHash.split('?')[0] || '';
    var hash = urlWithHashWithParams.split('#')[0];
    var isPrivate = videoInfo.vimeo[1] !== hash;
    if (isPrivate) {
        urlParams = urlParams.replace("/" + hash, '');
    }
    urlParams =
        urlParams[0] == '?' ? '&' + urlParams.slice(1) : urlParams || '';
    // For vimeo last params gets priority if duplicates found
    var vimeoPlayerParams = "?autoplay=0&muted=1" + (isPrivate ? "&h=" + hash : '') + defaultPlayerParams + urlParams;
    return vimeoPlayerParams;
};
//# sourceMappingURL=lg-video-utils.js.map