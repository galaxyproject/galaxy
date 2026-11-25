import createClient, { Middleware } from "openapi-fetch"
import type { paths as ToolShedApiPaths } from "./schema"
import { errorMessageAsString } from "@/util"

let client: ToolShedApiClient

export class ApiRequestError extends Error {
    constructor(
        readonly status: number,
        options?: ErrorOptions,
    ) {
        super(`Request failed with status ${status}`, options)
    }
}

function apiClientFactory() {
    const errorHandlingMiddleware: Middleware = {
        async onResponse({ response }) {
            if (!response.ok) {
                const message = response.headers.get("content-type")?.includes("json")
                    ? await response.clone().json()
                    : await response.clone().text()
                throw new ApiRequestError(response.status, { cause: errorMessageAsString(message) })
            }
            return response
        },
    }

    const client = createClient<ToolShedApiPaths>({ baseUrl: "" })

    client.use(errorHandlingMiddleware)

    return client
}

export type ToolShedApiClient = ReturnType<typeof apiClientFactory>

/**
 * Returns the Galaxy Tool Shed API client.
 *
 * It can be used to make requests to the Galaxy Tool Shed API using the OpenAPI schema.
 *
 * See: https://openapi-ts.dev/openapi-fetch/
 */
export function ToolShedApi() {
    if (!client) {
        client = apiClientFactory()
    }
    return client
}
