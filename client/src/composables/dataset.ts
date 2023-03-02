import { resolveUnref, type MaybeComputedRef } from "@vueuse/core";
import { ref, onScopeDispose, type Ref } from "vue";
import { rethrowSimple } from "@/utils/simple-error";
import { LastQueue } from "@/utils/promise-queue";
import { fetcher } from "@/schema";
import jobStatesModel from "@/utils/job-states-model";

const datasetFetcher = fetcher.path("/api/datasets/{dataset_id}").method("get").create();

function stateIsTerminal(result: { state: string }): boolean {
    return !jobStatesModel.NON_TERMINAL_STATES.includes(result.state);
}

type HTMLString = string;

// TODO: more explicit type
export type Dataset = {
    state: string;
    misc_blurb?: string;
    file_ext?: string;
    genome_build?: string;
    misc_info?: string;
    peek?: HTMLString;
    [key: string]: unknown;
};

export function useDataset(datasetId: MaybeComputedRef<string>, autoRefresh = false, refreshPeriod = 3000) {
    const isLoading = ref(true);
    const dataset: Ref<Dataset | null> = ref(null);
    const queue = new LastQueue(refreshPeriod);
    let timeout: ReturnType<typeof setTimeout> | null = null;

    const getDataset = async () => {
        try {
            const response = await datasetFetcher({ dataset_id: resolveUnref(datasetId) });
            return response.data;
        } catch (e) {
            rethrowSimple(e);
        }
    };

    const enqueueFetch = async () => {
        try {
            dataset.value = (await queue.enqueue(getDataset, [])) as Dataset;
            if (autoRefresh && !stateIsTerminal(dataset.value)) {
                timeout = setTimeout(enqueueFetch, refreshPeriod);
            }
        } catch (e) {
            console.error(`Failed to fetch dataset with id ${resolveUnref(datasetId)}. ${e}`);
        }
    };

    enqueueFetch();

    onScopeDispose(() => {
        if (timeout) {
            clearTimeout(timeout);
        }
    });

    return {
        isLoading,
        dataset,
    };
}
