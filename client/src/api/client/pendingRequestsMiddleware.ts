import type { Middleware } from "openapi-fetch";

import { getPendingAbortSignal, SKIP_PENDING_REQUESTS_HEADER } from "@/api/pendingRequests";

/**
 * Attaches the shared pending-requests signal to every ``GalaxyApi`` request.
 * The ``openapi-fetch`` client uses native ``fetch()`` so the axios
 * interceptor does not apply; without this middleware, login/register
 * navigations cannot cancel in-flight ``/api/...`` calls and a late
 * anonymous-cookie response can clobber the authenticated ``galaxysession``
 * cookie. See ``client/src/api/pendingRequests.ts`` for the race.
 */
export const pendingRequestsMiddleware: Middleware = {
    async onRequest({ request }) {
        if (request.headers.has(SKIP_PENDING_REQUESTS_HEADER)) {
            const headers = new Headers(request.headers);
            headers.delete(SKIP_PENDING_REQUESTS_HEADER);
            return new Request(request, { headers });
        }
        const shared = getPendingAbortSignal();
        // Combine with any signal the caller may have set so we don't silently
        // drop their cancellation semantics.
        const signal =
            typeof AbortSignal.any === "function" ? AbortSignal.any([request.signal, shared]) : shared;
        return new Request(request, { signal });
    },
};
