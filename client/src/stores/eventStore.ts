/**
 * Can be used to store data on events for access across components
 * e.g. to provide early drag event data transfer access.
 */

import { defineStore } from "pinia";
import { computed, type Ref, ref } from "vue";

export type EventData = { [key: string]: unknown };

export const useEventStore = defineStore("eventStore", () => {
    const dragData: Ref<EventData | null> = ref(null);
    const multipleDragData: Ref<boolean> = ref(false);
    const isMac = computed(() => navigator.userAgent.toUpperCase().indexOf("MAC") >= 0);

    function clearDragData() {
        dragData.value = null;
        multipleDragData.value = false;
    }

    function getDragData() {
        return dragData.value;
    }

    function getDragItems(): EventData[] {
        if (!dragData.value) {
            return [];
        }
        return multipleDragData.value ? (Object.values(dragData.value) as EventData[]) : [dragData.value];
    }

    function setDragData(data: EventData, multiple = false) {
        dragData.value = data;
        multipleDragData.value = multiple;
    }

    return {
        isMac,
        multipleDragData,
        clearDragData,
        getDragData,
        getDragItems,
        setDragData,
    };
});
