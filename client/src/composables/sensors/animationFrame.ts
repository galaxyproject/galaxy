import { onScopeDispose } from "vue";

type CallbackFunction = (timestamp: number) => void;

const callbacks: CallbackFunction[] = [];
let loopActive = false;

function animationFrameLoop(timestamp: number) {
    callbacks.forEach((callback) => {
        callback(timestamp);
    });

    window.requestAnimationFrame(animationFrameLoop);
}

/**
 * Runs a callback in the browsers animation loop.
 * This can serve as a performance effective alternative for frequently firing events (eg, scroll events)
 * @see https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame
 * @param callback
 * @returns a stop function, to remove the callback from the animation loop
 */
export function useAnimationFrame(callback: CallbackFunction) {
    callbacks.push(callback);

    if (!loopActive) {
        window.requestAnimationFrame(animationFrameLoop);
        loopActive = true;
    }

    const stop = () => {
        const index = callbacks.indexOf(callback);

        if (index !== -1) {
            callbacks.splice(index, 1);
        }
    };

    onScopeDispose(stop);

    return { stop };
}
