import { onBeforeUnmount, onMounted, type Ref, watch } from "vue";

/**
 * postMessage bridge for Galaxy's chrome-free embed surface
 * (`/published/page?embed=true`). When the page is framed by an external embedder
 * (e.g. a Loom/Orbit shell), it notifies the parent of lifecycle/size/navigation
 * events so the embedder can size the iframe and intercept link clicks instead of
 * navigating the whole Galaxy app inside a small pane.
 *
 * All messages are origin-restricted (never `*`): see {@link resolveEmbedTargetOrigin}.
 */

export const EMBED_MESSAGE_PREFIX = "galaxy-embed:";

export type EmbedMessage =
    | { type: "galaxy-embed:ready"; pageId: string }
    | { type: "galaxy-embed:height"; px: number }
    | { type: "galaxy-embed:title"; title: string }
    | { type: "galaxy-embed:navigate"; href: string };

/**
 * Resolve the origin to which embed postMessages may be sent. Prefer an explicit
 * origin (passed by the embedder via `?embed_origin=`); else the real parent origin
 * from `ancestorOrigins` (Chromium/Electron). Returns `null` when neither is known
 * -- callers then send nothing rather than fall back to the insecure `"*"`.
 */
export function resolveEmbedTargetOrigin(win: Window, explicitOrigin?: string): string | null {
    if (explicitOrigin) {
        return explicitOrigin;
    }
    const ancestors = win.location.ancestorOrigins;
    if (ancestors && ancestors.length > 0) {
        return ancestors[0] ?? null;
    }
    return null;
}

/**
 * Whether a clicked anchor should be routed to the parent rather than navigating
 * the embed iframe itself. In-page (`#...`) and `javascript:` links are left alone.
 */
export function shouldInterceptLink(href: string | null | undefined): boolean {
    if (!href) {
        return false;
    }
    const trimmed = href.trim();
    if (trimmed === "" || trimmed.startsWith("#") || trimmed.toLowerCase().startsWith("javascript:")) {
        return false;
    }
    return true;
}

export interface UseEmbedBridgeOptions {
    /** Only wire the bridge when rendering chrome-free (embedded). */
    enabled: boolean;
    pageId: string;
    /** Page title; emitted as `title` and re-emitted when it changes. */
    title: Ref<string | undefined>;
    /** Container whose size is observed and whose link clicks are intercepted. */
    root: Ref<HTMLElement | undefined | null>;
    /** Embedder origin from `?embed_origin=`; falls back to `ancestorOrigins`. */
    explicitOrigin?: string;
    /** Injectable for tests; defaults to the global `window`. */
    win?: Window;
}

/** `ResizeObserver` is a DOM global, not a member of the `Window` interface. */
type EmbedWindow = Window & { ResizeObserver?: typeof ResizeObserver };

export function useEmbedBridge(options: UseEmbedBridgeOptions): void {
    const win = (options.win ?? window) as EmbedWindow;
    // Nothing to do when disabled or when there is no distinct parent frame.
    if (!options.enabled || win.parent === win) {
        return;
    }
    const targetOrigin = resolveEmbedTargetOrigin(win, options.explicitOrigin);

    function post(message: EmbedMessage): void {
        if (!targetOrigin) {
            return;
        }
        win.parent.postMessage(message, targetOrigin);
    }

    let resizeObserver: ResizeObserver | undefined;

    function onClick(event: MouseEvent): void {
        const target = event.target as HTMLElement | null;
        const anchor = target?.closest?.("a") as HTMLAnchorElement | null;
        if (!anchor) {
            return;
        }
        const href = anchor.getAttribute("href");
        if (!shouldInterceptLink(href)) {
            return;
        }
        event.preventDefault();
        // Prefer the resolved absolute URL so the parent gets a navigable href.
        post({ type: "galaxy-embed:navigate", href: anchor.href || href! });
    }

    onMounted(() => {
        post({ type: "galaxy-embed:ready", pageId: options.pageId });
        if (options.title.value) {
            post({ type: "galaxy-embed:title", title: options.title.value });
        }
        const root = options.root.value;
        if (root) {
            root.addEventListener("click", onClick);
            if (typeof win.ResizeObserver !== "undefined") {
                const observer = new win.ResizeObserver(() => {
                    post({ type: "galaxy-embed:height", px: root.scrollHeight });
                });
                observer.observe(root);
                resizeObserver = observer;
            }
        }
    });

    watch(
        () => options.title.value,
        (title) => {
            if (title) {
                post({ type: "galaxy-embed:title", title });
            }
        },
    );

    onBeforeUnmount(() => {
        options.root.value?.removeEventListener("click", onClick);
        resizeObserver?.disconnect();
    });
}
