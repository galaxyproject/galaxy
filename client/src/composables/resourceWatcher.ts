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
 */
export function useResourceWatcher<T = unknown>(
    watchHandler: WatchResourceHandler,
    options: WatchOptions = DEFAULT_WATCH_OPTIONS
) {
    const { shortPollingInterval, longPollingInterval, enableBackgroundPolling } = {
        ...DEFAULT_WATCH_OPTIONS,
        ...options,
    };
    let currentPollingInterval = shortPollingInterval;
    let watchTimeout: NodeJS.Timeout | null = null;
    let isEventSetup = false;

    /**
     * Starts watching the resource by polling the server continuously.
     */
    function startWatchingResource(app?: T) {
        stopWatcher();
        tryWatchResource(app);
    }

    /**
     * Stops continuously watching the resource.
     */
    function stopWatchingResource() {
        stopWatcher();
    }

    function stopWatcher() {
        if (watchTimeout) {
            clearTimeout(watchTimeout);
            watchTimeout = null;
        }
    }

    async function tryWatchResource(app?: T) {
        try {
            await watchHandler(app);
        } catch (error) {
            console.warn(error);
        } finally {
            if (currentPollingInterval) {
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
            startWatchingResource();
        } else {
            currentPollingInterval = enableBackgroundPolling ? longPollingInterval : undefined;
        }
    }

    setupVisibilityListeners();

    return {
        startWatchingResource,
        stopWatchingResource,
    };
}
