/**
 * Run `callback` once the DOM is parsed, without waiting for the window `load` event,
 * which also waits for async third-party scripts and images.
 */
export function onDomReady(callback: () => void) {
    if (document.readyState !== "loading") {
        callback();
    } else {
        document.addEventListener("DOMContentLoaded", callback, { once: true });
    }
}
