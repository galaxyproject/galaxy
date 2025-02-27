import axios from "axios";

import { getAppRoot } from "@/onload/loadConfig";
import { rethrowSimple } from "@/utils/simple-error";

interface CacheEntry {
    data: any;
    timestamp: number;
}

const requestCache: Record<string, CacheEntry> = {};
const inProgress: Record<string, Promise<any>> = {};

export async function resetCache() {
    for (const key in requestCache) {
        delete requestCache[key];
    }
}

export async function fromCache(resource: string): Promise<any> {
    // Build resource url
    const url = `${getAppRoot()}api/${resource}`;

    // Check cache for valid entry
    const cached = requestCache[url];
    if (cached) {
        return cached.data;
    }

    // Avoid duplicate requests
    if (inProgress[url]) {
        return inProgress[url];
    }

    // Execute request
    try {
        const fetchPromise = axios.get(url).then(({ data }) => {
            requestCache[url] = { data, timestamp: Date.now() };
            delete inProgress[url];
            return data;
        });
        inProgress[url] = fetchPromise;
        return fetchPromise;
    } catch (e) {
        delete inProgress[url];
        rethrowSimple(e);
    }
}
