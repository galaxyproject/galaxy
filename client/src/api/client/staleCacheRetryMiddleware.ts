import type { Middleware } from "openapi-fetch";

import { isForeignHtmlResponse, NO_CACHE_HEADERS, REQUEST_ID_HEADER } from "@/api/staleCacheRetry";

/** ``openapi-fetch`` counterpart of ``installStaleCacheRetryInterceptor``, see ``@/api/staleCacheRetry``. */
export const staleCacheRetryMiddleware: Middleware = {
    async onResponse({ request, response }) {
        if (request.cache === "no-cache" || request.headers.get("Accept")?.includes("text/html")) {
            return response;
        }
        const isPoisoned = isForeignHtmlResponse({
            method: request.method,
            status: response.status,
            contentType: response.headers.get("content-type"),
            requestId: response.headers.get(REQUEST_ID_HEADER),
        });
        if (!isPoisoned) {
            return response;
        }
        console.warn(`Received foreign HTML for ${request.url}; retrying with the browser cache bypassed.`);
        const headers = new Headers(request.headers);
        for (const [name, value] of Object.entries(NO_CACHE_HEADERS)) {
            headers.set(name, value);
        }
        // Bypasses the rest of the middleware chain, like the rate limiter's retry.
        return fetch(new Request(request, { cache: "no-cache", headers }));
    },
};
