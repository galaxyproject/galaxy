/**
 * Helper to configure datatransfer for drag & drop operations
 */
import { type EventData, useEventStore } from "@/stores/eventStore";

export function setDrag(evt: DragEvent, data?: EventData, multiple = false) {
    const eventStore = useEventStore();
    if (data) {
        evt.dataTransfer?.setData("text", JSON.stringify([data]));
        // data submitted through datatransfer is only available upon drop,
        // in order to access the drop data immediately this event store is used.
        eventStore.setDragData(data, multiple);
    }
    if (evt.dataTransfer) {
        evt.dataTransfer.dropEffect = "move";
        evt.dataTransfer.effectAllowed = "move";
        const elem = document.getElementById("drag-ghost");
        if (elem) {
            evt.dataTransfer.setDragImage(elem, 0, 0);
        }
    }
}

export function clearDrag() {
    const eventStore = useEventStore();
    eventStore.clearDragData();
}
