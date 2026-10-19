import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

interface SerialTagSavesOptions {
    setTags: (tags: string[]) => void;
    /** Called when the last queued save failed. */
    onFailed: () => void;
}

/**
 * Saves tag edits in place, one after another, so an older tag list never lands after a newer one.
 * Once the queue drains, a failed last save calls ``onFailed``; otherwise the last saved tags are
 * shown again, since a list load that ran during the saves can hold the tags from before them.
 */
export function useSerialTagSaves({ setTags, onFailed }: SerialTagSavesOptions) {
    let tagsSaved: Promise<void> = Promise.resolve();
    let pendingTagSaves = 0;
    let lastSavedTags: string[] | undefined;
    let lastTagSaveFailed = false;

    function onTagSavesDone() {
        if (lastTagSaveFailed) {
            onFailed();
        } else if (lastSavedTags) {
            setTags(lastSavedTags);
        }
    }

    /** Shows ``tags`` now and queues ``save``, which stores them on the server. */
    function saveTags(tags: string[], save: () => Promise<unknown>) {
        setTags(tags);
        pendingTagSaves++;
        tagsSaved = tagsSaved.then(async () => {
            try {
                await save();
                lastSavedTags = tags;
                lastTagSaveFailed = false;
            } catch (error) {
                Toast.error(`Failed to save tags: ${errorMessageAsString(error)}`);
                lastTagSaveFailed = true;
            } finally {
                pendingTagSaves--;
                if (pendingTagSaves === 0) {
                    onTagSavesDone();
                }
            }
        });
    }

    return { saveTags };
}
