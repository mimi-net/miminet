"use strict";
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
    return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (_) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
var lg_events_1 = require("../../lg-events");
var lg_vimeo_thumbnail_settings_1 = require("./lg-vimeo-thumbnail-settings");
/**
 * Creates the vimeo thumbnails plugin.
 * @param {object} element - lightGallery element
 */
var VimeoThumbnail = /** @class */ (function () {
    function VimeoThumbnail(instance) {
        this.core = instance;
        // extend module default settings with lightGallery core settings
        this.settings = __assign(__assign({}, lg_vimeo_thumbnail_settings_1.vimeoSettings), this.core.settings);
        return this;
    }
    VimeoThumbnail.prototype.init = function () {
        var _this = this;
        if (!this.settings.showVimeoThumbnails) {
            return;
        }
        this.core.LGel.on(lg_events_1.lGEvents.init + ".vimeothumbnails", function (event) {
            var pluginInstance = event.detail.instance;
            var thumbCont = pluginInstance.$container
                .find('.lg-thumb-outer')
                .get();
            if (thumbCont) {
                _this.setVimeoThumbnails(pluginInstance);
            }
        });
    };
    VimeoThumbnail.prototype.setVimeoThumbnails = function (dynamicGallery) {
        return __awaiter(this, void 0, void 0, function () {
            var i, item, slideVideoInfo, response, vimeoInfo;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        i = 0;
                        _a.label = 1;
                    case 1:
                        if (!(i < dynamicGallery.galleryItems.length)) return [3 /*break*/, 5];
                        item = dynamicGallery.galleryItems[i];
                        slideVideoInfo = item.__slideVideoInfo || {};
                        if (!slideVideoInfo.vimeo) return [3 /*break*/, 4];
                        return [4 /*yield*/, fetch('https://vimeo.com/api/oembed.json?url=' +
                                encodeURIComponent(item.src))];
                    case 2:
                        response = _a.sent();
                        return [4 /*yield*/, response.json()];
                    case 3:
                        vimeoInfo = _a.sent();
                        dynamicGallery.$container
                            .find('.lg-thumb-item')
                            .eq(i)
                            .find('img')
                            .attr('src', this.settings.showThumbnailWithPlayButton
                            ? vimeoInfo.thumbnail_url_with_play_button
                            : vimeoInfo.thumbnail_url);
                        _a.label = 4;
                    case 4:
                        i++;
                        return [3 /*break*/, 1];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    VimeoThumbnail.prototype.destroy = function () {
        // Remove all event listeners added by vimeothumbnails plugin
        this.core.LGel.off('.lg.vimeothumbnails');
        this.core.LGel.off('.vimeothumbnails');
    };
    return VimeoThumbnail;
}());
exports.default = VimeoThumbnail;
//# sourceMappingURL=lg-vimeo-thumbnail.js.map