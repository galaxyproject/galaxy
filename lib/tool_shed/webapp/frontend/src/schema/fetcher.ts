import createClient, { Middleware } from "openapi-fetch"
import type { paths as ToolShedApiPaths } from "./schema"

const errorHandlingMiddleware: Middleware = {
    async onResponse({ response }) {
        if (!response.ok) {
            const errorMessage = response.headers.get("content-type")?.includes("json")
                ? await response.clone().json()
                : await response.clone().text()
            throw new Error(`Request failed with status ${response.status}`, {
                cause: errorMessage,
            })
        }
    },
}

const client = createClient<ToolShedApiPaths>({ baseUrl: "" })
client.use(errorHandlingMiddleware)

export { type ToolShedApiPaths, client }
