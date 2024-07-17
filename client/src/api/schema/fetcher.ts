import createClient from "openapi-fetch";
import { Fetcher, type Middleware } from "openapi-typescript-fetch";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

import { type paths as GalaxyApiPaths } from "./schema";

export type { GalaxyApiPaths };

const rethrowSimpleMiddleware: Middleware = async (url, init, next) => {
    try {
        const response = await next(url, init);
        return response;
    } catch (e) {
        rethrowSimple(e);
    }
};

export const fetcher = Fetcher.for<GalaxyApiPaths>();
fetcher.configure({ baseUrl: getAppRoot(undefined, true), use: [rethrowSimpleMiddleware] });

//TODO: add a Middleware to rethrow simple errors?
export const client = createClient<GalaxyApiPaths>({ baseUrl: getAppRoot(undefined, true) });
