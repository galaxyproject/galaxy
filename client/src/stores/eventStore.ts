/**
 * Can be used to store data on events for access across components
 * e.g. to provide early drag event data transfer access.
 */

import { ref, type Ref } from "vue";
import { defineStore } from "pinia";

export const useEventStore = defineStore("eventStore", () => {
    const dragEvent: Ref<{} | null> = ref(null);

    function clearDragEvent() {
        dragEvent.value = null;
    }

    function getDragEvent() {
        return dragEvent.value;
    }

    function setDragEvent(data: {}) {
        dragEvent.value = data;
    }

    return {
        clearDragEvent,
        getDragEvent,
        setDragEvent,
    };
});
