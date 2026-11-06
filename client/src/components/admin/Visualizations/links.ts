/** Return the URL if it's http(s), otherwise null; package metadata is untrusted and this page runs as an admin. */
export function externalUrl(value: unknown): string | null {
    if (typeof value !== "string") {
        return null;
    }
    try {
        const url = new URL(value);
        return url.protocol === "http:" || url.protocol === "https:" ? value : null;
    } catch {
        return null;
    }
}
