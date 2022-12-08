import { computed, unref } from "vue";

var idCounter = 0;

/**
 * Returns a page-unique id with and optional reactive prefix
 */
export function useUid(prefix = "") {
    const id = idCounter;
    idCounter += 1;

    const uid = computed(() => `${unref(prefix)}${id}`);
    return uid;
}
