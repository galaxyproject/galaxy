import { computed, ref } from "vue";

export function useMultiselect() {
    const editing = ref(false);
    const ariaExpanded = computed(() => {
        return editing.value ? "true" : "false";
    });

    function onOpen() {
        editing.value = true;
    }

    function onClose() {
        editing.value = false;
    }

    return { editing, ariaExpanded, onOpen, onClose };
}
