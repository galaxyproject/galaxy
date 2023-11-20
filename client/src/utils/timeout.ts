let timeoutHandler: ReturnType<typeof setTimeout> | null = null;
export const timeout = (callback: () => void, delay = 5000) => {
    if (timeoutHandler) {
        clearTimeout(timeoutHandler);
    }
    timeoutHandler = setTimeout(callback, delay);
};
