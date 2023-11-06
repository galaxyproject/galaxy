/**
 * Helper to configure datatransfer for drag & drop operations
 */
import { useEventStore } from "stores/eventStore";

export function setDrag(evt, data = null) {
    const eventStore = useEventStore();
    if (data) {
        evt.dataTransfer.setData("text", JSON.stringify([data]));
        // data submitted through datatransfer is only available upon drop,
        // in order to access the drop data immediately this event store is used.
        eventStore.setDragData(data);
    }
    evt.dataTransfer.dropEffect = "move";
    evt.dataTransfer.effectAllowed = "move";
    const elem = document.getElementById("drag-ghost");
    evt.dataTransfer.setDragImage(elem, 0, 0);
}

export function clearDrag() {
    const eventStore = useEventStore();
    eventStore.clearDragData();
}
