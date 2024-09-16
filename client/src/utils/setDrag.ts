/**
 * Helper to configure datatransfer for drag & drop operations
 */
import { type DCESummary, isDCE } from "@/api";
import { type EventData, useEventStore } from "@/stores/eventStore";

type NamedDCESummary = DCESummary & { name: string };

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

export function setItemDragstart<T>(
    item: T,
    event: DragEvent,
    itemIsSelected = false,
    selectionSize = 0,
    selectedItems?: Map<string, T>
) {
    if (selectedItems && itemIsSelected && selectionSize > 1) {
        const selectedItemsObj: Record<string, T> = {};
        for (const [key, value] of selectedItems) {
            setCollectionElementName(value as any);
            selectedItemsObj[key] = value;
        }
        setDrag(event, selectedItemsObj, true);
    } else {
        setCollectionElementName(item as any);
        setDrag(event, item as any);
    }
}

function setCollectionElementName<T extends NamedDCESummary>(obj: T) {
    if (isDCE(obj as object)) {
        obj["name"] = obj.element_identifier;
    }
}
