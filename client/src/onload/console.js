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
    let runningTest = false;

    if (process.env.NODE_ENV == "production") {
        defaultEnabled = false;
    } else if (process.env.NODE_ENV == "test") {
        runningTest = true;
    }

    const isEnabled = useLocalStorage("console-debugging-enabled", defaultEnabled);

    let storedConsole = null;

    const disableConsole = () => {
        console.log(
            "The Galaxy console has been disabled.  You can enable it by running enableDebugging() in devtools."
        );
        storedConsole = console;
        // eslint-disable-next-line no-global-assign
        console = {};
        Object.keys(storedConsole).forEach((key) => {
            console[key] = () => {};
        });
    };

    const enableConsole = () => {
        if (!runningTest) {
            console.log(
                "The Galaxy console has been enabled.  You can disable it by running disableDebugging() in devtools."
            );
        }
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
