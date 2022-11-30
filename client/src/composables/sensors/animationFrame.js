import { onScopeDispose } from "vue";

const callbacks = [];
var loopActive = false;

function animationFrameLoop(timestamp) {
    callbacks.forEach((callback) => {
        callback(timestamp);
    });

    window.requestAnimationFrame(animationFrameLoop);
}

/**
 * Runs a callback in the browsers animation loop.
 * This can serve as a performance effective alternative for frequently firing events (eg, scroll events)
 * @see https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame
 * @param {function} callback
 * @returns a stop function, to remove the callback from the animation loop
 */
export function useAnimationFrame(callback) {
    callbacks.push(callback);

    if (!loopActive) {
        window.requestAnimationFrame(animationFrameLoop);
        loopActive = true;
    }

    const stop = () => {
        var index = callbacks.indexOf(callback);

        if (index !== -1) {
            callbacks.splice(index, 1);
        }
    };

    onScopeDispose(stop);

    return { stop };
}
