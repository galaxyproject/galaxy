/**
 * Shared ``AbortController`` used by both the axios interceptor and the
 * ``openapi-fetch`` middleware so we can cancel every in-flight request in
 * one shot right before a login/register navigation.
 *
 * Why this exists: when the server processes a request that carries the old
 * anonymous ``galaxysession`` cookie *after* ``handle_user_login`` has marked
 * that session ``is_valid=False``, it creates a fresh anonymous session and
 * responds with ``Set-Cookie: galaxysession=<new>``. Delivered into the cookie
 * jar after the login response but before the new page loads, it overwrites
 * the just-issued authenticated cookie — so the new page loads anonymous and
 * ``wait_for_logged_in`` times out in selenium. Aborting the TCP connection
 * before the response headers are parsed prevents that ``Set-Cookie`` from
 * ever applying.
 */
import axios, { type InternalAxiosRequestConfig } from "axios";

let activeController = new AbortController();

/** Explicit opt-out header that the login/register POST itself sets. */
export const SKIP_PENDING_REQUESTS_HEADER = "x-galaxy-skip-pending-abort";

/**
 * The signal every request should ride on by default. Read lazily so the
 * ``openapi-fetch`` middleware picks up the fresh signal after each
 * ``cancelPendingRequests()`` rotation.
 */
export function getPendingAbortSignal(): AbortSignal {
    return activeController.signal;
}

/**
 * Install a request interceptor that attaches the shared signal to every
 * outgoing axios request that didn't set one itself. Call once at app boot.
 */
export function installPendingRequestsInterceptor() {
    axios.interceptors.request.use((config: InternalAxiosRequestConfig) => {
        if (config.signal !== undefined) {
            return config;
        }
        if (config.headers?.[SKIP_PENDING_REQUESTS_HEADER]) {
            delete config.headers[SKIP_PENDING_REQUESTS_HEADER];
            return config;
        }
        config.signal = activeController.signal;
        return config;
    });
}

/**
 * Abort every request that is using the shared signal (both axios via the
 * interceptor and ``openapi-fetch`` via its middleware) and install a fresh
 * controller so subsequent requests can still go out.
 */
export function cancelPendingRequests() {
    activeController.abort();
    activeController = new AbortController();
}
