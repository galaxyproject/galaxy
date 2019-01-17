import _ from "underscore";

function get(key, queryString) {
    queryString = queryString || window.location.search.substr(1);
    var keyRegex = new RegExp(`${key}=([^&#$]+)`, "g");
    var matches = queryString.match(keyRegex);
    if (!matches || !matches.length) {
        return undefined;
    }
    matches = _.map(matches, match => decodeURIComponent(match.substr(key.length + 1).replace(/\+/g, " ")));
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
    split.forEach(pairString => {
        var pair = pairString.split("=");
        parsed[pair[0]] = decodeURI(pair[1]);
    });
    return parsed;
}

// ============================================================================
export default {
    get: get,
    parse: parse
};
