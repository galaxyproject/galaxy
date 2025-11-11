// loadConfig.ts
let cachedConfig = null;

export async function loadConfig() {
    if (!cachedConfig) {
        try {
            const response = await fetch("/api/context");
            if (!response.ok) {
                throw new Error(`Failed to fetch /api/context (${response.status})`);
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
    let root = cachedConfig?.options?.root || defaultRoot;
    if (stripTrailingSlash) {
        root = root.replace(/\/$/, "");
    }
    return root;
}
