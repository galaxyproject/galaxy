import { http as rawHttp, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll } from "vitest";

import { GALAXY_RESPONSE_HEADERS, http, missingHandlerResponse } from "./http";

export { GALAXY_RESPONSE_HEADERS, HttpResponse };

let server: ReturnType<typeof setupServer>;
// How many callers' scopes are running. A test that mounts stories (whose helper sets the
// server up) may ask for it again, and a server listening twice handles every request twice.
let listeningScopes = 0;

function missingHandlerGuidance(request: Request) {
    const method = request.method.toLowerCase();
    const apiPath = request.url.replace(window.location.origin, "");
    return `Make sure you have added a request handler for this request in your tests.

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
    missingHandlerResponse(request, missingHandlerGuidance(request)),
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
    }

    beforeAll(() => {
        // Enable API mocking before all the tests.
        if (listeningScopes++ === 0) {
            server.listen();
        }
    });

    afterEach(() => {
        // Reset the request handlers between each test.
        // This way the handlers we add on a per-test basis
        // do not leak to other, irrelevant tests.
        server.resetHandlers();
    });

    afterAll(() => {
        // Finally, disable API mocking after the tests are done.
        if (--listeningScopes === 0) {
            server.close();
        }
    });

    return { server, http };
}
