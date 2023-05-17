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
