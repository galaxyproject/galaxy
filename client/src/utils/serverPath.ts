export function serverPath(rawUrl: string = window.location.href): string {
    const url = new URL(rawUrl);
    return url.pathname;
}
