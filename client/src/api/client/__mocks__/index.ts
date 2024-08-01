import { createOpenApiHttp } from "openapi-msw";

import { type GalaxyApiPaths } from "@/api/schema";

function createApiClientMock() {
    return createOpenApiHttp<GalaxyApiPaths>();
}

let clientMock: ReturnType<typeof createApiClientMock>;

export function useClientApiMock() {
    if (!clientMock) {
        clientMock = createApiClientMock();
    }

    return { clientMock };
}
