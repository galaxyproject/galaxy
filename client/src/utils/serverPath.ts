/**
 * Returns the path of the current or given URL.
 *
 * @param {string} [rawUrl=window.location.href]
 * @returns {string}
 */

export function serverPath(rawUrl: string = window.location.href): string {
    const url = new URL(rawUrl);
    return url.pathname;
}
