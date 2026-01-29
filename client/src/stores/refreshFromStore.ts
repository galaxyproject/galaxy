import { defineStore } from "pinia";
import { ref } from "vue";

/**
 * TODO: delete me
 *
 * This entire store and any code associated with it is a horrible hack.
 * It works around the Form Display Component not being reactive
 * to outside changes by forcing a refresh via the `key` prop.
 *
 * This is a bad practice.
 *
 * As soon as we get the Form to be reactive: delete this store!
 */
export const useRefreshFromStore = defineStore("refreshFormStore", () => {
    const formKey = ref(0);

    function refresh() {
        formKey.value += 1;
    }

    return {
        formKey,
        refresh,
    };
});
