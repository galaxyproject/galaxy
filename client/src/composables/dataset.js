import { ref } from "vue";
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

/**
 * Fetches a dataset's details // TODO: this will be in the store once it's broken apart.
 */

export function useDataset() {
    const datasetLoading = ref(true);
    const dataset = ref({});

    async function getDataset() {
        try {
            const datasetDetails = axios.get(`${getAppRoot()}api/dataset?extension_only=false`);
        } catch (e) {
            console.error("unable to fetch available dataset details\n", e);
        } finally {
            datasetLoading.value = false;
        }
    }

    getDataset();

    return { dataset, datasetLoading };
}
