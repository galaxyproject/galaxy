import { type ApiResponse, Fetcher, type Middleware } from "openapi-typescript-fetch";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

import { type paths } from "./schema";

export { type ApiResponse };

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
