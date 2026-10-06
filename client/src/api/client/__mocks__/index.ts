import { http as rawHttp, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { createOpenApiHttp } from "openapi-msw";
import { afterAll, afterEach, beforeAll } from "vitest";

import type { GalaxyApiPaths } from "@/api/schema";
import { REQUEST_ID_HEADER } from "@/api/staleCacheRetry";

export { HttpResponse };

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

function createApiClientMock() {
    return stampingHandlers(createOpenApiHttp<GalaxyApiPaths>({ baseUrl: window.location.origin }));
}

let http: ReturnType<typeof createApiClientMock>;
let server: ReturnType<typeof setupServer>;

function missingHandlerMessage(request: Request) {
    const method = request.method.toLowerCase();
    const apiPath = request.url.replace(window.location.origin, "");
    return `
No request handler found for ${request.method} ${request.url}.

Make sure you have added a request handler for this request in your tests.

Example:

const { server, http } = useServerMock();
server.use(
    http.${method}('${apiPath}', ({ response }) => {
        return response(200).json({});
    })
);
                `;
}

// Answers a request no test handled the way Galaxy answers an error, so the guidance
// reaches the caller as the error message. Tests' own handlers take precedence, and
// resetHandlers() keeps this one.
const missingHandlerFallback = rawHttp.all("*", ({ request }) =>
    HttpResponse.json(
        { err_msg: missingHandlerMessage(request), err_code: 500 },
        { status: 500, headers: GALAXY_RESPONSE_HEADERS },
    ),
);

/**
 * Returns a `server` instance that can be used to mock the Galaxy API server
 * and make requests to the Galaxy API using the OpenAPI schema.
 *
 * It is an instance of Mock Service Worker (MSW) server (https://github.com/mswjs/msw).
 * And the `http` object is an instance of OpenAPI-MSW (https://github.com/christoph-fricke/openapi-msw)
 * that add support for full type inference from OpenAPI schema definitions.
 */
export function useServerMock() {
    if (!server) {
        server = setupServer(missingHandlerFallback);
        http = createApiClientMock();
    }

    beforeAll(() => {
        // Enable API mocking before all the tests.
        server.listen();
    });

    afterEach(() => {
        // Reset the request handlers between each test.
        // This way the handlers we add on a per-test basis
        // do not leak to other, irrelevant tests.
        server.resetHandlers();
    });

    afterAll(() => {
        // Finally, disable API mocking after the tests are done.
        server.close();
    });

    return { server, http };
}
