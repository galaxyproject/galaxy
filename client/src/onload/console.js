/**
 * This module disables the console in production,
 * and adds the ability to toggle console logging
 * using the global functions
 * enableDebugging() and disableDebugging()
 */
import { useLocalStorage } from "@vueuse/core";
import { watch } from "vue";

export function overrideProductionConsole() {
    let defaultEnabled = true;

    if (process.env.NODE_ENV == "production") {
        defaultEnabled = false;
    }

    const isEnabled = useLocalStorage("console-debugging-enabled", defaultEnabled);

    let storedConsole = null;

    const disableConsole = () => {
        storedConsole = console;
        // eslint-disable-next-line no-global-assign
        console = {};
        Object.keys(storedConsole).forEach((key) => {
            console[key] = () => {};
        });
    };

    const enableConsole = () => {
        if (storedConsole) {
            // eslint-disable-next-line no-global-assign
            console = storedConsole;
        }
    };

    watch(
        () => isEnabled.value,
        (enabled) => {
            if (enabled) {
                enableConsole();
            } else {
                disableConsole();
            }
        },
        { immediate: true }
    );

    window.enableDebugging = () => {
        isEnabled.value = true;
    };

    window.disableDebugging = () => {
        isEnabled.value = false;
    };
}
