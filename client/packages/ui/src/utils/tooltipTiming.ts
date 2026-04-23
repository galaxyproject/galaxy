export const DEFAULT_TOOLTIP_HOVER_DELAY_MS = 300;
export const INTERACTIVE_POPOVER_CLOSE_DELAY_MS = 50;

export function useDelayedAction(delayMs: number) {
    let timer: ReturnType<typeof setTimeout> | null = null;

    return {
        schedule: (callback: () => void) => {
            if (timer !== null) {
                clearTimeout(timer);
            }
            timer = setTimeout(() => {
                timer = null;
                callback();
            }, delayMs);
        },
        clear: () => {
            if (timer !== null) {
                clearTimeout(timer);
                timer = null;
            }
        },
        isScheduled: () => timer !== null,
    };
}
