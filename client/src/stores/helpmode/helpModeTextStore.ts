/**
 * Stores Galaxy Help Mode's help content
 * TODO: Maybe this store is not needed and we have one singular `helpModeStore`?
 */

import { defineStore } from "pinia";
import { ref } from "vue";

import config from "./helpTextConfig.yml";

const DEFAULT_HELP_TEXT = "Welcome to Galaxy Help Mode!";

export const useHelpModeTextStore = defineStore("helpModeTextStore", () => {
    // TODO: We can store multiple help mode texts in the following variable, referenced by "content ids".
    // Then, `storeHelpModeText` can be modified to accept an id, and fetch and store the corresponding
    // help mode text. Then maybe we could have a tabbed interface within the help mode, we would prevent
    // multiple fetched for the same component or it would still open up other possibilities...
    // const contents = ref({});

    const content = ref(DEFAULT_HELP_TEXT);
    const loading = ref(false);

    /** Adds help mode text for the given Galaxy component `id` */
    async function storeHelpModeText(id: string) {
        const file_path = config[id];
        loading.value = true;
        await fetch("https://raw.githubusercontent.com/assuntad23/galaxy-help-markdown/main/" + file_path)
            .then((response) => response.text())
            .then((text) => {
                content.value = text;
                loading.value = false;
            });
    }

    function clearHelpModeText() {
        content.value = DEFAULT_HELP_TEXT;
    }

    return {
        content,
        loading,
        storeHelpModeText,
        clearHelpModeText,
    };
});
