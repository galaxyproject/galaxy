import type { Middleware } from "openapi-typescript-fetch";
import { Fetcher } from "openapi-typescript-fetch";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

import type { paths } from "./schema";

const rethrowSimpleMiddleware: Middleware = async (url, init, next) => {
    try {
        const response = await next(url, init);
        return response;
    } catch (e) {
        rethrowSimple(e);
    }
};

export const fetcher = Fetcher.for<paths>();
fetcher.configure({ baseUrl: getAppRoot(undefined, true), use: [rethrowSimpleMiddleware] });
