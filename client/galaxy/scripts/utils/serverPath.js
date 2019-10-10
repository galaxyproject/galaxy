export function serverPath(rawUrl = window.location.href) {
    let url = new URL(rawUrl);
    return url.pathname;
}
