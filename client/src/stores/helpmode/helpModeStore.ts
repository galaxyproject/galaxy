/**
 * A pinia store for the Galaxy Help Mode.
 */

import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { defineStore, storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { rethrowSimple } from "@/utils/simple-error";

import { useUserStore } from "../userStore";
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

    const { toggledSideBar } = storeToRefs(useUserStore());

    const draggableActive = ref(false);
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
    /** The ids of the components for which help text was requested while help mode was disabled */
    const idsToStore = ref<string[]>([]);

    const status = computed(() => toggledSideBar.value === "help" || draggableActive.value);

    // if side bar is toggled to help mode, if draggable is active, set it to false
    watch(toggledSideBar, (newVal) => {
        if (newVal === "help" && draggableActive.value) {
            draggableActive.value = false;
        }
    });

    // when help mode is enabled, store help for the ids requested while help mode was disabled
    watch(status, async (newStatus) => {
        if (newStatus) {
            for (const id of idsToStore.value) {
                await storeHelpModeText(id);
            }
            idsToStore.value = [];
        }
    });

    async function storeHelpModeText(id: string, icon?: IconDefinition) {
        // if help mode is disabled, store the id in the temp array and return
        if (!status.value) {
            idsToStore.value.push(id);
            return;
        }

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
        // if help mode is disabled, remove the id from the temp array
        if (!status.value) {
            const idx = idsToStore.value.indexOf(id);
            if (idx !== -1) {
                idsToStore.value.splice(idx, 1);
            }
        }

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
        /** Whether the draggble help mode is active or not */
        draggableActive,
        /** Removes the tab from the stack for the given component `id` */
        clearHelpModeText,
        /** Adds help mode text for the given Galaxy component `id` if help mode is enabled */
        storeHelpModeText,
    };
});
