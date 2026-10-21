// Storybook's service worker is as strict as the unit test server: an /api/ request
// that no story handler answers gets Galaxy's 500, and the story fails afterwards.
import { http as rawHttp } from "msw";
import { setupWorker } from "msw/browser";

import { missingHandlerResponse } from "@/api/client/__mocks__/http";

const isApiRequest = (request: Request) => new URL(request.url).pathname.startsWith("/api/");

const unmockedRequests: string[] = [];
let inFlight = 0;
let lastActivity = 0;

const unmockedApiFallback = rawHttp.all("/api/*", ({ request }) => {
    unmockedRequests.push(`${request.method} ${new URL(request.url).pathname}`);
    return missingHandlerResponse(request, "Add a handler for it to the story's `parameters.msw.handlers`.");
});

/** Starts the worker for `mswLoader()`. resetHandlers() between stories keeps the fallback. */
export async function setupStoryWorker() {
    const worker = setupWorker(unmockedApiFallback);
    worker.events.on("request:start", ({ request }) => {
        if (isApiRequest(request)) {
            inFlight++;
            lastActivity = performance.now();
        }
    });
    worker.events.on("request:end", ({ request }) => {
        if (isApiRequest(request)) {
            inFlight--;
            lastActivity = performance.now();
        }
    });
    await worker.start({ quiet: true, onUnhandledRequest: "bypass" });
    return worker;
}

/**
 * Waits until no API request is in flight and none has started for `quietMs`, so
 * requests a story fires while rendering are seen before it is checked.
 */
async function settle(quietMs = 50, timeoutMs = 2000) {
    const deadline = performance.now() + timeoutMs;
    do {
        await new Promise((resolve) => setTimeout(resolve, 10));
    } while ((inFlight > 0 || performance.now() - lastActivity < quietMs) && performance.now() < deadline);
}

/** Clears unmocked requests left over from an earlier story. */
export function resetUnmockedRequests() {
    unmockedRequests.splice(0);
}

/** Fails the story if it made API requests no handler answered. */
export async function failOnUnmockedRequests() {
    await settle();
    const unmocked = unmockedRequests.splice(0);
    if (unmocked.length) {
        throw new Error(
            `Unmocked API requests:\n${unmocked.join("\n")}\nAdd handlers to the story's parameters.msw.handlers.`,
        );
    }
}
