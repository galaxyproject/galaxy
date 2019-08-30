export function serverPath(rawUrl = window.location.href) {
    const url = new URL(rawUrl);
    return url.pathname;
}
