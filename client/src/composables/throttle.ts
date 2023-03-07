import { useAnimationFrame } from "./sensors/animationFrame";

export function useAnimationFrameThrottle() {
    let lastCallback: (() => void) | null = null;

    const throttle = (callback: () => void) => {
        lastCallback = callback;
    };

    useAnimationFrame(() => {
        if (lastCallback) {
            lastCallback();
            lastCallback = null;
        }
    });

    return {
        throttle,
    };
}
