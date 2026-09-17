import type { Middleware } from "openapi-fetch";

interface RateLimitConfig {
    /** Maximum requests per window */
    maxRequests?: number;
    /** Time the requestwindow lasts in milliseconds */
    windowMs?: number;
    /** Delay between retries on 429 */
    retryDelay?: number;
    /** Maximum retry attempts */
    maxRetries?: number;
}

export const DEFAULT_CONFIG: Required<RateLimitConfig> = {
    maxRequests: 100,
    windowMs: 60000,
    retryDelay: 1000,
    maxRetries: 3,
};

/**
 * Rate limiting middleware to control the rate of API requests.
 *
 * Uses a timed window and only allows a maximum number of requests per that window.
 */
export function createRateLimiterMiddleware(config: RateLimitConfig = {}): Middleware {
    const cfg = { ...DEFAULT_CONFIG, ...config };

    let requestCount = 0;
    let windowStart = Date.now();

    /** Resets the request window if the time has elapsed */
    function resetWindowIfNeeded() {
        const now = Date.now();
        if (now - windowStart >= cfg.windowMs) {
            requestCount = 0;
            windowStart = now;
        }
    }

    /** Places a request in the rate limiter queue */
    async function placeRequestInQueue(): Promise<void> {
        resetWindowIfNeeded();

        if (requestCount < cfg.maxRequests) {
            requestCount++;
            return;
        }

        // Rate limit exceeded, wait for next window
        const waitTime = cfg.windowMs - (Date.now() - windowStart);

        await new Promise((resolve) => setTimeout(resolve, waitTime));

        // After waiting, try again (this will reset the window)
        return placeRequestInQueue();
    }

    const middleware: Middleware = {
        async onRequest({ request }) {
            await placeRequestInQueue();
            return request;
        },

        async onResponse({ response: res, request }) {
            // Handle 429 Too Many Requests from server
            if (res.status === 429 && request.method === "GET") {
                const retryAfter = res.headers.get("Retry-After");
                const delay = retryAfter ? parseInt(retryAfter) * 1000 : cfg.retryDelay;

                console.warn(`Received 429 from server, waiting ${delay}ms before retry`);

                let retries = 0;
                while (retries < cfg.maxRetries) {
                    retries++;
                    await new Promise((resolve) => setTimeout(resolve, delay));

                    // A tricky thing here is that we will bypass the middleware chain on retry
                    const retryResponse = await fetch(request);
                    if (retryResponse.status !== 429) {
                        return retryResponse;
                    }
                    console.warn(`Retry ${retries} also received 429, retrying...`);
                }

                console.error(`Max retries reached for request to ${request.url}`);
            }

            return res;
        },
    };

    return middleware;
}
