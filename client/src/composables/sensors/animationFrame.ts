import { onScopeDispose } from "vue";

type CallbackFunction = (timestamp: number) => void;
interface CallbackGroup {
    priority: number;
    callbacks: CallbackFunction[];
}

const callbackGroups: CallbackGroup[] = [];
let loopActive = false;

function animationFrameLoop(timestamp: number) {
    callbackGroups.forEach((group) => {
        group.callbacks.forEach((callback) => {
            callback(timestamp);
        });
    });

    window.requestAnimationFrame(animationFrameLoop);
}

function getCallbackGroup(priority: number): CallbackGroup {
    let group = callbackGroups.find((g) => g.priority === priority);

    if (group) {
        return group;
    } else {
        group = {
            priority,
            callbacks: [],
        };

        callbackGroups.push(group);
        callbackGroups.sort((a, b) => b.priority - a.priority);

        return group;
    }
}

/**
 * Runs a callback in the browsers animation loop.
 * This can serve as a performance effective alternative for frequently firing events (eg, scroll events)
 * @see https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame
 * @param callback
 * @param priority higher priority callbacks get called first
 * @returns a stop function, to remove the callback from the animation loop
 */
export function useAnimationFrame(callback: CallbackFunction, priority = 0) {
    const group = getCallbackGroup(priority);

    group.callbacks.push(callback);

    if (!loopActive) {
        window.requestAnimationFrame(animationFrameLoop);
        loopActive = true;
    }

    const stop = () => {
        const index = group.callbacks.indexOf(callback);

        if (index !== -1) {
            group.callbacks.splice(index, 1);
        }
    };

    onScopeDispose(stop);

    return { stop };
}
