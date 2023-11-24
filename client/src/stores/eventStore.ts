/**
 * Can be used to store data on events for access across components
 * e.g. to provide early drag event data transfer access.
 */

import { ref, type Ref } from "vue";
import { defineStore } from "pinia";

export type EventData = { [key: string]: unknown };

export const useEventStore = defineStore("eventStore", () => {
    const dragData: Ref<EventData | null> = ref(null);

    function clearDragData() {
        dragData.value = null;
    }

    function getDragData() {
        return dragData.value;
    }

    function setDragData(data: EventData) {
        dragData.value = data;
    }

    return {
        clearDragData,
        getDragData,
        setDragData,
    };
});
