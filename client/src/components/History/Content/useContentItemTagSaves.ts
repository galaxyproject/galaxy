import { watch } from "vue";

import type { HistoryItemSummary } from "@/api";
import { fetchCollectionSummary } from "@/api/datasetCollections";
import { fetchDatasetDetails } from "@/api/datasets";
import { updateContentFields } from "@/components/History/model/queries";
import { useSerialTagSaves } from "@/composables/serialTagSaves";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

type SetTags = (tags: string[]) => void;

// ListingLayout remounts rows on refresh, so queues must outlive their row instances.
const tagSaves = new Map<string, ReturnType<typeof createTagSaves>>();

function createTagSaves(key: string, item: HistoryItemSummary) {
    const listeners = new Set<SetTags>();
    let pending = 0;
    let tagVersion = 0;
    let currentTags: string[] = [];

    function cleanup() {
        if (!pending && !listeners.size && tagSaves.get(key) === queue) {
            tagSaves.delete(key);
        }
    }

    function setTags(tags: string[]) {
        tagVersion++;
        currentTags = tags;
        listeners.forEach((listener) => listener(tags));
        cleanup();
    }

    const serial = useSerialTagSaves({
        setTags,
        onFailed: async () => {
            const failedVersion = tagVersion;
            pending++;
            try {
                const storedItem = await (item.history_content_type === "dataset_collection"
                    ? fetchCollectionSummary({ hdca_id: item.id })
                    : fetchDatasetDetails({ id: item.id }));
                if (tagVersion === failedVersion) {
                    setTags(storedItem.tags);
                }
            } catch (error) {
                Toast.error(`Failed to reload tags: ${errorMessageAsString(error)}`);
            } finally {
                pending--;
                cleanup();
            }
        },
    });

    const queue = {
        subscribe(listener: SetTags) {
            listeners.add(listener);
            if (pending) {
                listener(currentTags);
            }
            return () => {
                listeners.delete(listener);
                cleanup();
            };
        },
        saveTags(tags: string[], save: () => Promise<string[]>) {
            pending++;
            serial.saveTags(tags, async () => {
                try {
                    return await save();
                } finally {
                    // Cleanup waits for the serial helper's final notification.
                    pending--;
                }
            });
        },
    };
    return queue;
}

function tagSavesFor(key: string, item: HistoryItemSummary) {
    let queue = tagSaves.get(key);
    if (!queue) {
        queue = createTagSaves(key, item);
        tagSaves.set(key, queue);
    }
    return queue;
}

export function useContentItemTagSaves(
    item: () => HistoryItemSummary,
    getItemKey: (item: HistoryItemSummary) => string,
    setTags: (item: HistoryItemSummary, tags: string[]) => void,
) {
    watch(
        () => getItemKey(item()),
        (key, _previous, onCleanup) => {
            onCleanup(tagSavesFor(key, item()).subscribe((tags) => setTags(item(), tags)));
        },
        { immediate: true, flush: "sync" },
    );

    return (tags: string[]) => {
        const content = item();
        tagSavesFor(getItemKey(content), content).saveTags(
            tags,
            async () => (await updateContentFields(content, { tags })).tags ?? tags,
        );
    };
}
