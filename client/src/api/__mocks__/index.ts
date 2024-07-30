import { createOpenApiHttp } from "openapi-msw";

import { type GalaxyApiPaths } from "@/api";

const clientMock = createOpenApiHttp<GalaxyApiPaths>();

export { clientMock };
