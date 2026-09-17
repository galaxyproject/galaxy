import { computed, type Ref } from "vue";

import { useDatasetCollectionStore } from "@/stores/datasetCollectionStore";
import { useDatasetStore } from "@/stores/datasetStore";
import { errorMessageAsString } from "@/utils/simple-error";

/**
 * Reactive lookup of the job that produced a given dataset (HDA) or collection
 * (HDCA). Reads through the existing keyed-cache stores so concurrent callers
 * dedupe and switching the input ref naturally re-targets without races — an
 * in-flight response for an older id can never overwrite the current one.
 *
 * For HDCAs, only collections produced by a single Job have a resolvable
 * creating job; batch / workflow collections surface a friendly explanation.
 * `job_source_id` / `job_source_type` are on the HDCA summary, so a cached
 * summary suffices — no detail upgrade is forced here.
 */
export function useCreatingJob(itemId: Ref<string | null>, itemSrc: Ref<string | null>) {
    const datasetStore = useDatasetStore();
    const collectionStore = useDatasetCollectionStore();

    const isHda = computed(() => itemSrc.value === "hda" && !!itemId.value);
    const isHdca = computed(() => itemSrc.value === "hdca" && !!itemId.value);

    // Reading through these accessors triggers an on-demand fetch on first
    // access and stays reactive as the store updates.
    const dataset = computed(() => (isHda.value ? datasetStore.getDataset(itemId.value!) : null));
    const collection = computed(() => (isHdca.value ? collectionStore.getCollection(itemId.value!) : null));

    const datasetError = computed(() => (isHda.value ? datasetStore.getDatasetError(itemId.value!) : null));
    const collectionError = computed(() => (isHdca.value ? collectionStore.getCollectionError(itemId.value!) : null));

    const jobId = computed<string | null>(() => {
        if (isHda.value) {
            return dataset.value?.creating_job ?? null;
        }
        if (isHdca.value && collection.value?.job_source_type === "Job") {
            return collection.value.job_source_id ?? null;
        }
        return null;
    });

    const loading = computed(() => {
        if (isHda.value) {
            return !dataset.value && !datasetError.value;
        }
        if (isHdca.value) {
            return !collection.value && !collectionError.value;
        }
        return false;
    });

    const error = computed<string | null>(() => {
        if (isHda.value) {
            if (datasetError.value) {
                return errorMessageAsString(datasetError.value);
            }
            if (dataset.value && !dataset.value.creating_job) {
                return "No creating job recorded for this dataset.";
            }
            return null;
        }
        if (isHdca.value) {
            if (collectionError.value) {
                return errorMessageAsString(collectionError.value);
            }
            if (collection.value && collection.value.job_source_type !== "Job") {
                return "This collection was not produced by a specific identifiable job.";
            }
            return null;
        }
        return null;
    });

    return { jobId, loading, error };
}
