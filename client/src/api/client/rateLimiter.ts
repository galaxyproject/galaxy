import type { Middleware } from "openapi-fetch";

import { parseRetryAfterMs, retryBackoffMs } from "@/utils/simple-error";

interface RateLimitConfig {
    /** Maximum requests per window */
    maxRequests?: number;
    /** Time the requestwindow lasts in milliseconds */
    windowMs?: number;
    /** Base delay before the first retry on 429; doubles per retry, with jitter */
    retryDelay?: number;
    /** Upper bound for a single retry delay; a longer Retry-After stops retrying */
    maxRetryDelay?: number;
    /** Maximum retry attempts */
    maxRetries?: number;
}

export const DEFAULT_CONFIG: Required<RateLimitConfig> = {
    maxRequests: 100,
    windowMs: 60000,
    retryDelay: 1000,
    maxRetryDelay: 5000,
    maxRetries: 3,
};

/**
 * Rate limiting middleware to control the rate of API requests.
 *
 * Uses a timed window and only allows a maximum number of requests per that window.
 */
export function createRateLimiterMiddleware(config: RateLimitConfig = {}): Middleware {
    const cfg = { ...DEFAULT_CONFIG, ...config };

    /**
     * Jittered exponential backoff before the 1-based retry `attempt`, honoring a numeric Retry-After.
     * Null when Retry-After exceeds `maxRetryDelay`, since retrying sooner would only hit 429 again.
     */
    function retryDelayMs(attempt: number, response: Response, url: string): number | null {
        const retryAfter = parseRetryAfterMs(response.headers);
        if (retryAfter !== undefined && retryAfter > cfg.maxRetryDelay) {
            console.warn(`Retry-After of ${retryAfter}ms exceeds ${cfg.maxRetryDelay}ms, not retrying ${url}`);
            return null;
        }
        return Math.round(retryBackoffMs(attempt, retryAfter, cfg.retryDelay, cfg.maxRetryDelay));
    }

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
                const firstDelay = retryDelayMs(1, res, request.url);
                if (firstDelay === null) {
                    return res;
                }
                let delay = firstDelay;
                console.warn(`Received 429 from server, waiting ${delay}ms before retry`);

                let retries = 0;
                let retryResponse = res;
                while (retries < cfg.maxRetries) {
                    retries++;
                    await new Promise((resolve) => setTimeout(resolve, delay));

                    // A tricky thing here is that we will bypass the middleware chain on retry
                    retryResponse = await fetch(request);
                    if (retryResponse.status !== 429) {
                        return retryResponse;
                    }
                    if (retries < cfg.maxRetries) {
                        const nextDelay = retryDelayMs(retries + 1, retryResponse, request.url);
                        if (nextDelay === null) {
                            return retryResponse;
                        }
                        delay = nextDelay;
                        console.warn(`Retry ${retries} also received 429, retrying in ${delay}ms...`);
                    } else {
                        console.warn(`Retry ${retries} also received 429`);
                    }
                }

                console.error(`Max retries reached for request to ${request.url}`);
                return retryResponse;
            }

            return res;
        },
    };

    return middleware;
}
