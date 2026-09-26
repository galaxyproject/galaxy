import { useAnimationFrame } from "./sensors/animationFrame";

export function useAnimationFrameThrottle(animationFramePriority = 0) {
    let lastCallback: (() => void) | null = null;

    const throttle = (callback: () => void) => {
        lastCallback = callback;
    };

    useAnimationFrame(() => {
        if (lastCallback) {
            lastCallback();
            lastCallback = null;
        }
    }, animationFramePriority);

    return {
        throttle,
    };
}

type TimeoutThrottleCallback = (() => void) | (() => Promise<void>);

/**
 * Throttles a function with a timeout in milliseconds.
 * Will call the provided function immediately, and subsequent throttle calls
 * only after provided timeout period. Unlike the equivalent function from VueUse,
 * this will always call the last provided callback eventually.
 */
export function useTimeoutThrottle(timeout = 100) {
    let lastCallback: TimeoutThrottleCallback | null = null;
    let pendingTimeout = false;

    const throttle = (callback: TimeoutThrottleCallback) => {
        lastCallback = callback;
        run();
    };

    const run = async () => {
        const nextCallback = lastCallback;

        if (!pendingTimeout && nextCallback) {
            pendingTimeout = true;
            lastCallback = null;
            await nextCallback();

            setTimeout(() => {
                pendingTimeout = false;
                run();
            }, timeout);
        }
    };

    return {
        throttle,
    };
}
