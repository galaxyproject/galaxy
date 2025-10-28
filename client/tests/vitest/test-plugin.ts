import { Plugin } from "vite";

// Plugin to handle i18n! imports
export function i18nPlugin(): Plugin {
    return {
        name: "i18n-mock",
        resolveId(id: string) {
            if (id.startsWith("i18n!")) {
                return "\0" + id;
            }
        },
        load(id: string) {
            if (id.startsWith("\0i18n!")) {
                // Return a mock module
                return `export default {};`;
            }
        },
    };
}