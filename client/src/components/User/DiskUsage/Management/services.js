import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export async function fetchDiscardedDatasets() {
    const keys = "id,name,size,update_time";
    const isDataset = "q=history_content_type-eq&qv=dataset";
    const isDeleted = "q=deleted-eq&qv=True";
    const isNotPurged = "q=purged-eq&qv=False";
    const url = `${getAppRoot()}api/datasets?keys=${keys}&${isDataset}&${isDeleted}&${isNotPurged}`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
