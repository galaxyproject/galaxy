import { computed, unref } from "vue";
import type { Ref } from "vue";

let idCounter = 0;

/**
 * Returns a page-unique id with and optional reactive prefix
 */
export function useUid(prefix: string | Ref<string> = "") {
    const id = idCounter;
    idCounter += 1;

    const uid = computed(() => `${unref(prefix)}${id}`);
    return uid;
}
