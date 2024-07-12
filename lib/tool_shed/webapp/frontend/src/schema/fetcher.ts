import createClient from "openapi-fetch"
import type { paths as ToolShedApiPaths } from "./schema"

const client = createClient<ToolShedApiPaths>({ baseUrl: "" })
export { type ToolShedApiPaths, client }
