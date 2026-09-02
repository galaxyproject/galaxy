/**
 * Retries GET/HEAD responses that the browser served from a cache entry
 * poisoned by a failover page.
 *
 * A failover page answering every path with a cacheable ``200 text/html``
 * (nginx ``try_files ... /index.html`` without ``Cache-Control``) gets cached
 * under whatever URL the client requested during the outage. Stable URLs such
 * as the history panel's initial contents fetch then keep returning that HTML
 * for as long as heuristic freshness lasts, which can be weeks.
 *
 * Galaxy stamps ``X-Request-ID`` on every response and the cache keeps
 * response headers, so HTML without it did not come from Galaxy. Such a
 * response is re-requested with ``Cache-Control: no-cache``: Galaxy ignores
 * the failover page's validators and answers 200, replacing the cached body.
 * Genuine HTML served by a file server or object store (no request id) only
 * costs a conditional request answered with 304.
 */
import axios, { AxiosHeaders, type AxiosInstance, type AxiosResponse } from "axios";

export const NO_CACHE_HEADERS: Readonly<Record<string, string>> = {
    "Cache-Control": "no-cache",
    Pragma: "no-cache",
};

export const REQUEST_ID_HEADER = "X-Request-ID";

const CACHEABLE_METHODS = ["get", "head"];

interface ResponseDescription {
    method: string | undefined;
    status: number;
    contentType: string | null | undefined;
    requestId: string | null | undefined;
}

/** True for a successful ``GET``/``HEAD`` answered with an HTML page that Galaxy did not produce. */
export function isForeignHtmlResponse({ method, status, contentType, requestId }: ResponseDescription): boolean {
    if (!CACHEABLE_METHODS.includes((method ?? "get").toLowerCase())) {
        return false;
    }
    if (status < 200 || status >= 300) {
        return false;
    }
    if (!contentType || !contentType.toLowerCase().startsWith("text/html")) {
        return false;
    }
    return !requestId;
}

/**
 * Registers a response interceptor on ``instance`` (the global axios by
 * default) that retries foreign HTML answers with the cache bypassed. Call
 * once at app boot.
 */
export function installStaleCacheRetryInterceptor(instance: AxiosInstance = axios) {
    instance.interceptors.response.use(async (response: AxiosResponse) => {
        const config = response.config;
        const responseType = config.responseType ?? "json";
        if (responseType !== "json") {
            return response;
        }
        const alreadyRetried = config.headers.get("Cache-Control") === NO_CACHE_HEADERS["Cache-Control"];
        if (alreadyRetried) {
            return response;
        }
        const isPoisoned = isForeignHtmlResponse({
            method: config.method,
            status: response.status,
            contentType: String(response.headers["content-type"] ?? ""),
            requestId: String(response.headers[REQUEST_ID_HEADER.toLowerCase()] ?? ""),
        });
        if (!isPoisoned) {
            return response;
        }
        const url = instance.getUri(config);
        console.warn(`Received foreign HTML for ${url}; retrying with the browser cache bypassed.`);
        const headers = new AxiosHeaders(config.headers).set(NO_CACHE_HEADERS);
        return instance.request({ ...config, headers });
    });
}
