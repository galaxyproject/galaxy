import { defer, Subject } from "rxjs";
import { filter, finalize, share } from "rxjs/operators";

// global XHR request feed, emits every time xhr fires
const xhr$ = defer(() => {
    const request$ = new Subject();

    // patch
    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (method, url) {
        request$.next({ method, url });
        return originalOpen.apply(this, arguments);
    };

    return request$.pipe(
        // un-patch after all subscribers have left
        finalize(() => {
            XMLHttpRequest.prototype.open = originalOpen;
        })
    );
}).pipe(share());

/**
 * Watch outgoing ajax calls for any of the indicated methods, filter to any of the provided route regexes
 *
 * @param {Object} cfg  Configure methods and routes to monitor
 * @return {Observable} Observable that emits every time a matching outgoing request happens
 */
export const monitorXHR = (cfg = {}) => {
    return xhr$.pipe(filter(matchRoutes(cfg)));
};

// matches incoming method/url against config
export const matchRoutes =
    (cfg = {}) =>
    ({ method, url }) => {
        const { methods = ["GET", "POST", "PUT", "DELETE"], routes = [], exclude = [] } = cfg;

        // match fun compares route def to current url
        const matcher = matchUrlToRoute(url);

        if (!methods.includes(method)) {
            return false;
        }
        if (exclude.length && exclude.find(matcher)) {
            return false;
        }
        if (routes.length) {
            const routeMatch = routes.find(matcher);
            return !!routeMatch;
        }
        return false;
    };

const matchUrlToRoute = (url) => (rt) => {
    let result = false;
    if (rt instanceof RegExp) {
        result = url.match(rt);
    } else {
        // simple matcher
        result = url.includes(rt);
    }
    return result;
};
