/**
 * Messages and URL checks shared by the "Choose from another Galaxy" picker, which runs in a popup on the
 * source Galaxy, and the upload method on the target Galaxy that opened it.
 */

export const PICKER_PROTOCOL = 1;

export type PickedItemType = "dataset" | "dataset_collection";

export interface PickedItem {
    type: PickedItemType;
    name: string;
    /** Short term storage link of the item's export on the source Galaxy. */
    link: string;
}

/** Sent by the picker once it is open, so the target knows the source Galaxy supports the picker. */
export interface PickerHello {
    type: "galaxy-picker/hello";
    protocol: typeof PICKER_PROTOCOL;
    version: string;
    /** Root URL of the source Galaxy, which its links start with; the address the user typed may be a deeper page. */
    root: string;
    nonce: string;
}

/** Sent by the picker after the user confirmed what to send. */
export interface PickerResult {
    type: "galaxy-picker/result";
    protocol: typeof PICKER_PROTOCOL;
    nonce: string;
    items: PickedItem[];
    /** How many chosen items could not be exported; the popup closes on this message, so the target has to say so. */
    failed: number;
}

/** Sent by the picker when the user gave up without sending anything. */
export interface PickerCancel {
    type: "galaxy-picker/cancel";
    nonce: string;
}

export type PickerMessage = PickerHello | PickerResult | PickerCancel;

const PICKED_ITEM_TYPES: readonly string[] = ["dataset", "dataset_collection"];
const LOCAL_HOSTS = ["localhost", "127.0.0.1", "[::1]"];
const DEFAULT_PORTS: Record<string, string> = { "http:": ":80", "https:": ":443" };
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// URL parsers drop or rewrite whitespace, control characters and backslashes, so the result is not what was written.
function hasUnsafeCharacters(raw: string): boolean {
    return Array.from(raw).some((char) => {
        const code = char.charCodeAt(0);
        return code <= 0x20 || (code >= 0x7f && code <= 0x9f) || char === "\\";
    });
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === "string" && value.length > 0;
}

function isPickedItem(value: unknown): value is PickedItem {
    return (
        isRecord(value) &&
        typeof value.type === "string" &&
        PICKED_ITEM_TYPES.includes(value.type) &&
        typeof value.name === "string" &&
        isNonEmptyString(value.link)
    );
}

export function isPickerHello(data: unknown): data is PickerHello {
    return (
        isRecord(data) &&
        data.type === "galaxy-picker/hello" &&
        data.protocol === PICKER_PROTOCOL &&
        typeof data.version === "string" &&
        isNonEmptyString(data.root) &&
        isNonEmptyString(data.nonce)
    );
}

export function isPickerResult(data: unknown): data is PickerResult {
    return (
        isRecord(data) &&
        data.type === "galaxy-picker/result" &&
        data.protocol === PICKER_PROTOCOL &&
        isNonEmptyString(data.nonce) &&
        Array.isArray(data.items) &&
        data.items.every(isPickedItem) &&
        Number.isInteger(data.failed) &&
        (data.failed as number) >= 0
    );
}

export function isPickerCancel(data: unknown): data is PickerCancel {
    return isRecord(data) && data.type === "galaxy-picker/cancel" && isNonEmptyString(data.nonce);
}

/**
 * Parses an http(s) URL whose authority must read the same before and after parsing: no credentials, and no
 * spelling (percent-encoding, full-width dots, numeric IPv4 forms) that URL rewrites into another host.
 * Plain http is accepted only for localhost.
 */
function parseHttpUrl(raw: string, rest: RegExp): { url: URL; path: string } | null {
    if (hasUnsafeCharacters(raw)) {
        return null;
    }
    const match = new RegExp(`^(https?)://([^/?#@]+)(${rest.source})$`, "i").exec(raw);
    if (!match) {
        return null;
    }
    let url: URL;
    try {
        url = new URL(raw);
    } catch {
        return null;
    }
    const scheme = url.protocol;
    if (scheme !== "https:" && !(scheme === "http:" && LOCAL_HOSTS.includes(url.hostname))) {
        return null;
    }
    const authority = match[2]!.toLowerCase();
    const defaultPort = DEFAULT_PORTS[scheme]!;
    const writtenHost = authority.endsWith(defaultPort) ? authority.slice(0, -defaultPort.length) : authority;
    if (writtenHost !== url.host) {
        return null;
    }
    return { url, path: match[3]! };
}

/**
 * The origin the picker may send its result to, from the target's `return` query parameter.
 * Accepts only an origin (an optional "/" but no path, query or fragment) over https, or http on localhost.
 * @returns The normalized origin, or null when `raw` is anything else.
 */
export function parseReturnOrigin(raw: unknown): string | null {
    if (typeof raw !== "string") {
        return null;
    }
    const parsed = parseHttpUrl(raw, /\/?/);
    return parsed ? parsed.url.origin : null;
}

export interface SourceGalaxy {
    /** Origin the picker's messages must come from. */
    origin: string;
    /** Root URL of the Galaxy, with its path prefix and a trailing slash, e.g. https://example.org/galaxy/ */
    root: string;
}

/**
 * The Galaxy a user typed in to choose items from. Same scheme and host rules as `parseReturnOrigin`,
 * but a path prefix is kept. A URL without a scheme is read as https.
 * @returns The source's origin and root, or null when `raw` is not such a URL.
 */
export function parseSourceUrl(raw: unknown): SourceGalaxy | null {
    if (typeof raw !== "string") {
        return null;
    }
    let typed = raw.trim();
    if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(typed)) {
        typed = `https://${typed}`;
    }
    const parsed = parseHttpUrl(typed, /[^?#]*/);
    // URL resolves dot segments and encodes some characters; a path it rewrote is not the one typed.
    if (!parsed || (parsed.path || "/") !== parsed.url.pathname) {
        return null;
    }
    const { origin, pathname } = parsed.url;
    return { origin, root: `${origin}${pathname.endsWith("/") ? pathname : `${pathname}/`}` };
}

/**
 * Whether `link` is a short term storage download link on the source Galaxy with root `root`
 * (as returned by `parseSourceUrl`), and nothing else.
 */
export function isLinkFromSource(link: unknown, root: string): boolean {
    const prefix = `${root}api/short_term_storage/`;
    return typeof link === "string" && link.startsWith(prefix) && UUID.test(link.slice(prefix.length));
}

/**
 * Whether `value` can be a nonce the picker echoes back: a short string of URL-safe characters. It is opaque to the
 * picker, so a target may use another generator than `makeNonce`.
 */
export function isPickerNonce(value: unknown): value is string {
    return typeof value === "string" && /^[A-Za-z0-9_-]{16,128}$/.test(value);
}

/** A random 128 bit value, as hex, that ties a picker's result to the request that opened it. */
export function makeNonce(): string {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
