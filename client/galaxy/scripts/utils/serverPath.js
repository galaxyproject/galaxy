export function serverPath(rawUrl) {
    let url = new URL(rawUrl);
    return url.pathname;
}
