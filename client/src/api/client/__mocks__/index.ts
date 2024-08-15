import { HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { createOpenApiHttp } from "openapi-msw";

import { type GalaxyApiPaths } from "@/api/schema";

export { HttpResponse };

function createApiClientMock() {
    return createOpenApiHttp<GalaxyApiPaths>({ baseUrl: window.location.origin });
}

let http: ReturnType<typeof createApiClientMock>;
let server: ReturnType<typeof setupServer>;

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
        server = setupServer();
        http = createApiClientMock();
    }

    beforeAll(() => {
        // Enable API mocking before all the tests.
        server.listen({
            onUnhandledRequest: (request) => {
                const method = request.method.toLowerCase();
                const apiPath = request.url.replace(window.location.origin, "");
                const errorMessage = `
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
                throw new Error(errorMessage);
            },
        });
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
