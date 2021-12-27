import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

export async function fetchDiscardedDatasets() {
    const url = `${getAppRoot()}api/datasets?keys=id,name,size,update_time&q=history_content_type-eq&qv=dataset&q=purged-eq&qv=False&q=deleted-eq&qv=True`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}
