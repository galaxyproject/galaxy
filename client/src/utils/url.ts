import axios from "axios";

import { withPrefix } from "@/utils/redirect";
import { rethrowSimple } from "@/utils/simple-error";

export interface UrlDataOptions {
    url: string;
    headers?: Record<string, string>;
    params?: Record<string, string>;
    errorSimplify?: boolean;
}

export async function urlData<R>({ url, headers, params, errorSimplify = true }: UrlDataOptions): Promise<R> {
    try {
        headers = headers || {};
        params = params || {};
        const { data } = await axios.get(withPrefix(url), { headers, params });
        return data as R;
    } catch (e) {
        if (errorSimplify) {
            rethrowSimple(e);
        } else {
            throw e;
        }
    }
}

/**
 * Adds search parameters to url.
 *
 * @param original url
 * @param params which will be added to the url
 * @returns
 */
export function addSearchParams(url: string, params: Record<string, string>) {
    const placeholder = url.indexOf("?") == -1 ? "?" : "&";
    const searchParams = new URLSearchParams(params);
    const searchString = searchParams.toString();
    return searchString ? `${url}${placeholder}${searchString}` : url;
}
