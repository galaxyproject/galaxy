// Browser-safe half of the API mocks: typed request handlers, shared by the
// node test server (./index.ts) and Storybook's service worker.
import { HttpResponse } from "msw";
import { createOpenApiHttp } from "openapi-msw";

import type { GalaxyApiPaths } from "@/api/schema";
import { REQUEST_ID_HEADER } from "@/api/staleCacheRetry";

/** Headers Galaxy puts on every response, for tests that build responses with plain `msw`. */
export const GALAXY_RESPONSE_HEADERS: Readonly<Record<string, string>> = {
    [REQUEST_ID_HEADER]: "mocked-request-id",
};

// Galaxy stamps every response it produces with a request id, and the client treats
// a failed response without one as coming from a proxy. Successful responses are
// left alone so tests can still describe a foreign one.
function withGalaxyRequestId(response: unknown) {
    if (response instanceof Response && !response.ok && !response.headers.has(REQUEST_ID_HEADER)) {
        response.headers.set(REQUEST_ID_HEADER, GALAXY_RESPONSE_HEADERS[REQUEST_ID_HEADER]!);
    }
    return response;
}

function stampingHandlers<T extends object>(registry: T): T {
    return new Proxy(registry, {
        get(target, method, receiver) {
            const member: unknown = Reflect.get(target, method, receiver);
            if (method === "untyped" && typeof member === "object" && member !== null) {
                return stampingHandlers(member);
            }
            if (typeof member !== "function") {
                return member;
            }
            return (path: unknown, resolver: (...args: any[]) => unknown, ...rest: unknown[]) =>
                member(path, async (...args: any[]) => withGalaxyRequestId(await resolver(...args)), ...rest);
        },
    });
}

/**
 * Galaxy's answer to a request no handler matched: a 500 whose error message names the
 * request and says how to mock it, so the guidance reaches whatever made the call.
 */
export function missingHandlerResponse(request: Request, guidance: string) {
    return HttpResponse.json(
        { err_msg: `\nNo request handler found for ${request.method} ${request.url}.\n\n${guidance}`, err_code: 500 },
        { status: 500, headers: GALAXY_RESPONSE_HEADERS },
    );
}

/** Typed Galaxy API handlers, shared by the vitest mock server and stories. */
export const http = stampingHandlers(createOpenApiHttp<GalaxyApiPaths>({ baseUrl: window.location.origin }));

/** Answers `GET /api/configuration` with these settings, for components that read the config store. */
export function configurationHandler(config: Record<string, unknown>) {
    return http.get("/api/configuration", ({ response }) => response.untyped(HttpResponse.json(config)));
}

/**
 * Requests the app makes on any page, answered with empty defaults. Storybook's preview
 * and `useStoryMount()` install these under their names, so a story overrides one by
 * declaring a handler with the same name.
 */
export const appHandlers = {
    configuration: configurationHandler({}),
    datatypes: http.get("/api/datatypes", ({ response }) => response(200).json([])),
};
