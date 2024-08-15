import { Fetcher } from "openapi-typescript-fetch"
import type { paths } from "./schema"

/*
import type { Middleware } from "openapi-typescript-fetch";
import { rethrowSimple } from "@/utils/simple-error";
const rethrowSimpleMiddleware: Middleware = async (url, init, next) => {
    try {
        const response = await next(url, init);
        return response;
    } catch (e) {
        rethrowSimple(e);
    }
};

use: [rethrowSimpleMiddleware]
*/

export const fetcher = Fetcher.for<paths>()
fetcher.configure({ baseUrl: "" })
