import { readonly, ref } from "vue";

export type WatchResourceHandler<T = unknown> = (app?: T) => Promise<void>;

export interface WatchOptions {
    /**
     * Polling interval in milliseconds when the app is active (in the current tab).
     */
    shortPollingInterval?: number;
    /**
     * Polling interval in milliseconds when the app is in the background (not in the current tab).
     */
    longPollingInterval?: number;
    /**
     * If true, the resource is watched in the background even when the app is not active (in the current tab).
     */
    enableBackgroundPolling?: boolean;
}

const DEFAULT_WATCH_OPTIONS: WatchOptions = {
    shortPollingInterval: 3000,
    longPollingInterval: 10000,
    enableBackgroundPolling: true,
};

/**
 * Creates a composable that watches a resource by polling the server continuously.
 * By default, the polling interval is 'short' when the app is active (in the current tab) and 'long'
 * when the app is in the background (not in the current tab).
 * You can also completely disable background polling by setting `enableBackgroundPolling` to false in the options.
 * @param watchHandler The handler function that watches the resource by querying the server.
 * @param options Options to customize the polling interval.
 * @returns An object with functions to start/stop watching and check the current watching state.
 */
export function useResourceWatcher<T = unknown>(
    watchHandler: WatchResourceHandler,
    options: WatchOptions = DEFAULT_WATCH_OPTIONS,
) {
    const { shortPollingInterval, longPollingInterval, enableBackgroundPolling } = {
        ...DEFAULT_WATCH_OPTIONS,
        ...options,
    };
    let currentPollingInterval = shortPollingInterval;
    let watchTimeout: NodeJS.Timeout | null = null;
    let isEventSetup = false;

    /** ID to track the current request to prevent duplicate polling */
    let currentRequestId = 0;
    const isWatchingResource = ref<boolean>(false);

    /**
     * Starts watching the resource by polling the server continuously.
     */
    function startWatchingResource(app?: T) {
        stopWatcher();
        isWatchingResource.value = true;
        tryWatchResource(app);
    }

    /**
     * Stops continuously watching the resource.
     */
    function stopWatchingResource() {
        stopWatcher();
    }

    /**
     * Starts watching the resource if it is not already being watched.
     */
    function startWatchingResourceIfNeeded() {
        if (!isWatchingResource.value) {
            startWatchingResource();
        }
    }

    /**
     * Stops watching the resource if it is currently being watched.
     */
    function stopWatchingResourceIfNeeded() {
        if (isWatchingResource.value) {
            stopWatchingResource();
        }
    }

    function stopWatcher() {
        isWatchingResource.value = false;

        // Update the request ID to invalidate any in-flight requests
        currentRequestId++;

        if (watchTimeout) {
            clearTimeout(watchTimeout);
            watchTimeout = null;
        }
    }

    async function tryWatchResource(app?: T) {
        // Capture the current request ID to ensure we only schedule the next poll
        const requestId = currentRequestId;
        try {
            await watchHandler(app);
        } catch (error) {
            console.warn(error);
        } finally {
            // Only schedule next poll if still watching and no new requests have been made
            if (currentPollingInterval && isWatchingResource.value && requestId === currentRequestId) {
                watchTimeout = setTimeout(() => {
                    tryWatchResource(app);
                }, currentPollingInterval);
            }
        }
    }

    function setupVisibilityListeners() {
        if (!isEventSetup) {
            isEventSetup = true;
            document.addEventListener("visibilitychange", updateThrottle);
        }
    }

    function updateThrottle() {
        if (document.visibilityState === "visible") {
            currentPollingInterval = shortPollingInterval;
            startWatchingResourceIfNeeded();
        } else {
            if (enableBackgroundPolling) {
                currentPollingInterval = longPollingInterval;
            } else {
                // Stop watching when tab is not visible and background polling is disabled
                currentPollingInterval = undefined;
                stopWatchingResourceIfNeeded();
            }
        }
    }

    setupVisibilityListeners();

    return {
        /**
         * Starts watching the resource by polling the server continuously.
         * @param app Optional parameter to pass to the watch handler.
         */
        startWatchingResource,
        /**
         * Stops continuously watching the resource.
         */
        stopWatchingResource,
        startWatchingResourceIfNeeded,
        stopWatchingResourceIfNeeded,
        /**
         * Reactive boolean ref indicating whether the resource watcher is currently active.
         */
        isWatchingResource: readonly(isWatchingResource),
    };
}
