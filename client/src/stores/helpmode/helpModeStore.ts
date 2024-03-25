/**
 * A pinia store for the Galaxy Help Mode.
 */

import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { defineStore } from "pinia";
import { ref } from "vue";

import { rethrowSimple } from "@/utils/simple-error";

import config from "./helpTextConfig.yml";

interface HelpContent {
    title: string;
    content: string;
    icon?: IconDefinition;
}
interface HelpModeStyle {
    width: string;
    height: string;
    top?: string;
    left?: string;
}

export const DEFAULT_HELP_TEXT = "Welcome to Galaxy Help Mode!";

export const useHelpModeStore = defineStore("helpModeStore", () => {
    // TODO: Maybe `status` should be tracked in local storage?
    // const status: Ref<boolean> = useUserLocalStorage("help-mode-status", false);

    const status = ref(false);
    const position = ref({ x: 0, y: 0 });
    const helpModeStyle = ref<HelpModeStyle>({
        width: "25%",
        height: "30%",
    });
    const contents = ref<Record<string, HelpContent>>({});
    const activeTab = ref<string | null>(null);
    const loading = ref(false);
    const currentTabs = ref<string[]>([]);
    /** Component ids for which fetching the help text was unsuccessful */
    const invalidIds = ref<string[]>([]);

    async function storeHelpModeText(id: string, icon?: IconDefinition) {
        loading.value = true;
        try {
            // Error handling
            if (invalidIds.value.includes(id)) {
                // this id has been marked as invalid, don't try to fetch or throw an error again
                return;
            }
            if (!config[id]) {
                throw new Error(`No help mode config found for ${id}`);
            }

            const { title, file_path } = config[id];

            // if the text is already stored, don't fetch it again
            if (!contents.value[id]) {
                const response = await fetch(
                    "https://raw.githubusercontent.com/assuntad23/galaxy-help-markdown/main/" + file_path
                );
                const text = await response.text();
                contents.value[id] = { title, content: text, icon };
            }

            // set the active tab to the id
            activeTab.value = id;
            // move this id to the top of the stack
            currentTabs.value.push(id);
        } catch (error) {
            console.error(`Failed to fetch help mode text for ${id}`, error);
            invalidIds.value.push(id);
            rethrowSimple(error);
        } finally {
            loading.value = false;
        }
    }

    function clearHelpModeText(id: string) {
        // remove id from currentTabs
        const idx = currentTabs.value.indexOf(id);
        if (idx !== -1) {
            currentTabs.value.splice(idx, 1);
        }

        // from tabs, get the last element (or null if there is none left)
        const currId = currentTabs.value[currentTabs.value.length - 1] || null;
        activeTab.value = currId;
    }

    return {
        /** The tab currently active in help mode */
        activeTab,
        /** Stores `HelpContent`s by component ids */
        contents,
        /** A stack of the tabs currently in context */
        currentTabs,
        /** The css styling of the help mode */
        helpModeStyle,
        loading,
        /** The css position of the help mode */
        position,
        /** Whether help mode is active or not */
        status,
        /** Removes the tab from the stack for the given component `id` */
        clearHelpModeText,
        /** Adds help mode text for the given Galaxy component `id` */
        storeHelpModeText,
    };
});
