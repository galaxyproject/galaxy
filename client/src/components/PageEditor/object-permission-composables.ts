import { computed, type Ref, ref } from "vue";

import { referencedObjects } from "@/components/Markdown/parse";

interface ObjectVueRefs {
    referencedJobIds: Ref<string[]>;
    referencedHistoryDatasetIds: Ref<string[]>;
    referencedHistoryDatasetCollectionIds: Ref<string[]>;
    referencedWorkflowIds: Ref<string[]>;
    referencedInvocationIds: Ref<string[]>;
}

export function initializeObjectReferences(): ObjectVueRefs {
    const referencedJobIds = ref<string[]>([]);
    const referencedHistoryDatasetIds = ref<string[]>([]);
    const referencedHistoryDatasetCollectionIds = ref<string[]>([]);
    const referencedWorkflowIds = ref<string[]>([]);
    const referencedInvocationIds = ref<string[]>([]);
    return {
        referencedJobIds,
        referencedHistoryDatasetIds,
        referencedHistoryDatasetCollectionIds,
        referencedWorkflowIds,
        referencedInvocationIds,
    };
}

export function updateReferences(objectsRefs: ObjectVueRefs, markdown: string) {
    const {
        referencedJobIds,
        referencedHistoryDatasetIds,
        referencedHistoryDatasetCollectionIds,
        referencedWorkflowIds,
        referencedInvocationIds,
    } = objectsRefs;

    const objects = referencedObjects(markdown);

    referencedJobIds.value = Array.from(objects.jobs.values());
    referencedHistoryDatasetIds.value = Array.from(objects.historyDatasets.values());
    referencedHistoryDatasetCollectionIds.value = Array.from(objects.historyDatasetCollections.values());
    referencedWorkflowIds.value = Array.from(objects.workflows.values());
    referencedInvocationIds.value = Array.from(objects.invocations.values());
}

export function initializeObjectToHistoryRefs(referenceObjects: ObjectVueRefs) {
    const jobsToHistories: Ref<{ [key: string]: string }> = ref({});
    const invocationsToHistories: Ref<{ [key: string]: string }> = ref({});
    const historyDatasetCollectionsToHistories: Ref<{ [key: string]: string }> = ref({});

    const historyIds = computed<string[]>(() => {
        // be sure to reference all refs required for full computation
        const jobIds = referenceObjects.referencedJobIds.value;
        const jobMapping = jobsToHistories.value;

        const invocationIds = referenceObjects.referencedInvocationIds.value;
        const invocationMapping = invocationsToHistories.value;

        const collectionIds = referenceObjects.referencedHistoryDatasetCollectionIds.value;
        const collectionMapping = historyDatasetCollectionsToHistories.value;

        const theHistories = new Set();

        for (const jobId of jobIds) {
            if (jobId in jobMapping) {
                theHistories.add(jobMapping[jobId]);
            }
        }
        for (const invocationId of invocationIds) {
            if (invocationId in invocationMapping) {
                theHistories.add(invocationMapping[invocationId]);
            }
        }
        for (const historyDatasetCollectionId of collectionIds) {
            if (historyDatasetCollectionId in collectionMapping) {
                theHistories.add(collectionMapping[historyDatasetCollectionId]);
            }
        }
        const historyIds = Array.from(theHistories.values()) as string[];
        return historyIds;
    });

    return {
        jobsToHistories,
        invocationsToHistories,
        historyDatasetCollectionsToHistories,
        historyIds,
    };
}
