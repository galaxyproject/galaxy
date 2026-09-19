/**
 * Composable for "open in window-manager frame when active, else navigate inline".
 *
 * The window-manager-aware navigation pattern recurs across components
 * (HistoryCounter, HistoryPageView, PageEditorView, ContentItem, etc.):
 *
 * 1. Check ``Galaxy?.frame?.active``.
 * 2. When active: push a *framed* URL (typically with ``?displayOnly=true``
 *    or ``?embed=true``) plus a ``title`` option, so the monkeypatched
 *    ``router.push`` (``client/src/entry/analysis/router-push.js``)
 *    intercepts and opens it as a floating frame.
 * 3. When inactive: push the *inline* URL plainly.
 */
import type VueRouter from "vue-router";
import type { RawLocation } from "vue-router";
import { isNavigationFailure } from "vue-router";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import type { RouterPushOptions } from "@/components/History/Content/router-push-options";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

interface FrameOrPageOptions {
    /** URL to push when the window manager is active. Typically carries ``?displayOnly=true``/``?embed=true``. */
    framedUrl: string;
    /** URL to push otherwise. Defaults to ``framedUrl``. */
    inlineUrl?: string;
    /** Title shown on the floating frame's tab. Required for the monkeypatch to open a frame. */
    title: string;
    /** Forwards ``RouterPushOptions.force`` -- the monkeypatch's ``__vkey__`` trick for re-pushing the same URL. */
    force?: boolean;
}

/**
 * Pushes without treating a cancelled navigation as an error.
 *
 * A guard answering ``next(false)`` rejects the push, and so does re-pushing the current
 * route; neither is a failure worth surfacing. Anything else is, so it is reported rather
 * than dropped. The monkeypatched push (``entry/analysis/router-push.js``) also returns
 * nothing at all when the window manager takes the navigation or a confirmation is
 * declined, so there is not always a promise to attach to.
 */
export function pushIgnoringNavCancel(router: VueRouter, location: RawLocation, options?: RouterPushOptions): void {
    const pushed: Promise<unknown> | undefined = options
        ? // @ts-ignore - monkeypatched router accepts a second options argument; drop with migration.
          router.push(location, options)
        : router.push(location);
    pushed?.catch((error) => {
        if (!isNavigationFailure(error)) {
            Toast.error(errorMessageAsString(error), "Navigation failed");
        }
    });
}

export function useWindowAwareNavigation() {
    const router = useRouter();

    function pushToFrameOrPage({ framedUrl, inlineUrl, title, force }: FrameOrPageOptions): void {
        const Galaxy = getGalaxyInstance();
        if (Galaxy?.frame?.active) {
            const options: RouterPushOptions = { title, preventWindowManager: false };
            if (force) {
                options.force = true;
            }
            pushIgnoringNavCancel(router, framedUrl, options);
        } else {
            const target = inlineUrl ?? framedUrl;
            pushIgnoringNavCancel(router, target, force ? { force: true } : undefined);
        }
    }

    return { pushToFrameOrPage };
}
