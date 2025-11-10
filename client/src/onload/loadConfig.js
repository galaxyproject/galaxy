// loadConfig.ts
export async function loadConfig() {
    try {
        const response = await fetch("/api/context");
        if (!response.ok) {
            throw new Error(`Failed to fetch /api/context (${response.status})`);
        }
        const config = await response.json();
        return config;
    } catch (err) {
        console.error("Failed to load Galaxy configuration:", err);
        return {};
    }
}

let cachedConfig = null;

export async function getConfig() {
    if (!cachedConfig) {
        cachedConfig = await loadConfig();
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
