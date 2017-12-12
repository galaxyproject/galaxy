define("utils/query-string-parsing", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    // ============================================================================
    function get(key, queryString) {
        queryString = queryString || window.location.search.substr(1);
        var keyRegex = new RegExp(key + "=([^&#$]+)", "g");
        var matches = queryString.match(keyRegex);
        if (!matches || !matches.length) {
            return undefined;
        }
        matches = _.map(matches, function(match) {
            return decodeURIComponent(match.substr(key.length + 1).replace(/\+/g, " "));
        });
        if (matches.length === 1) {
            return matches[0];
        }
        return matches;
    }

    function parse(queryString) {
        if (!queryString) {
            return {};
        }
        var parsed = {};
        var split = queryString.split("&");
        split.forEach(function(pairString) {
            var pair = pairString.split("=");
            parsed[pair[0]] = decodeURI(pair[1]);
        });
        return parsed;
    }

    // ============================================================================
    exports.default = {
        get: get,
        parse: parse
    };
});
//# sourceMappingURL=../../maps/utils/query-string-parsing.js.map
