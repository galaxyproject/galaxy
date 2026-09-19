import { serverPath } from "@/utils/serverPath";

let cachedConfig = null;

export async function loadConfig() {
    if (!cachedConfig) {
        try {
            const response = await fetch(`${getAppRoot()}context`);
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

/**
 * Finds <link rel="index"> in head element and pulls root url fragment from
 * there.
 *
 * @param {string} [defaultRoot="/"]
 * @returns {string}
 */
export function getAppRoot(defaultRoot = "/") {
    if (typeof document === "undefined") {
        return defaultRoot;
    }
    const links = document.getElementsByTagName("link");
    const indexLink = Array.from(links).find((link) => link.rel == "index");
    return indexLink && indexLink.href ? serverPath(indexLink.href) : defaultRoot;
}
