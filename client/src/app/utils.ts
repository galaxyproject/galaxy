import { getAppRoot } from "@/onload/loadConfig";

/**
 * Get the full URL path of the app
 *
 * @param path Path to append to the URL path
 * @returns Full URL path of the app
 */
export function getFullAppUrl(path: string = ""): string {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port ? `:${window.location.port}` : "";
    const appRoot = getAppRoot();

    return `${protocol}//${hostname}${port}${appRoot}${path}`;
}
