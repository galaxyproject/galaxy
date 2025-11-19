// loadConfig.ts
import { getRootFromIndexLink } from "@/onload/getRootFromIndexLink";

let cachedConfig = null;

export async function loadConfig() {
    if (!cachedConfig) {
        try {
            const root = getRootFromIndexLink();
            const response = await fetch(`${root}context`);
            if (!response.ok) {
                throw new Error(`Failed to fetch /context (${response.status})`);
            }
            cachedConfig = await response.json();
        } catch (err) {
            console.error("Failed to load Galaxy configuration:", err);
            return {};
        }
    }
    return cachedConfig;
}

export function getAppRoot(defaultRoot = "/", stripTrailingSlash = false) {
    let root = cachedConfig?.root || defaultRoot;
    if (stripTrailingSlash) {
        root = root.replace(/\/$/, "");
    }
    return root;
}
