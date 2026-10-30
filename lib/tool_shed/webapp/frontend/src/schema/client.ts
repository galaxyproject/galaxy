import createClient, { Middleware } from "openapi-fetch"
import type { paths as ToolShedApiPaths } from "./schema"
import { errorMessageAsString } from "@/util"

let client: ToolShedApiClient

/** The one route whose trailing `{path}` param holds a slash-separated file path. */
export const FILE_CONTENTS_PATH =
    "/api/repositories/{encoded_repository_id}/revisions/{changeset_revision}/files/{path}" satisfies keyof ToolShedApiPaths

function apiClientFactory() {
    const errorHandlingMiddleware: Middleware = {
        async onResponse({ response }) {
            if (!response.ok) {
                const message = response.headers.get("content-type")?.includes("json")
                    ? await response.clone().json()
                    : await response.clone().text()
                throw new Error(`Request failed with status ${response.status}`, {
                    cause: errorMessageAsString(message),
                })
            }
            return response
        },
    }

    // openapi-fetch escapes the file path param whole; put its slashes back since some proxies reject %2F
    const filePathMiddleware: Middleware = {
        async onRequest({ request, schemaPath }) {
            if (schemaPath !== FILE_CONTENTS_PATH) {
                return undefined
            }
            const url = new URL(request.url)
            const segments = url.pathname.split("/")
            const prefixLength = FILE_CONTENTS_PATH.split("/").length - 1
            url.pathname = [
                ...segments.slice(0, prefixLength),
                segments.slice(prefixLength).join("/").replace(/%2F/gi, "/"),
            ].join("/")
            return new Request(url, request)
        },
    }

    const client = createClient<ToolShedApiPaths>({ baseUrl: "" })

    client.use(filePathMiddleware)
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
