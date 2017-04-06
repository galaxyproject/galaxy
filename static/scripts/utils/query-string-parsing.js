define([],function(){function n(n,e){e=e||window.location.search.substr(1);var t=new RegExp(n+"=([^&#$]+)"),r=e.match(t);if(r&&r.length)return r=r.splice(1),1===r.length?r[0]:r}function e(n){if(!n)return{};var e={};return n.split("&").forEach(function(n){var t=n.split("=");e[t[0]]=decodeURI(t[1])}),e}return{get:n,parse:e}});
//# sourceMappingURL=../../maps/utils/query-string-parsing.js.map
