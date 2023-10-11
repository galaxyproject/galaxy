import axios from "axios";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";

async function getDatasetCollection({ id }) {
    const url = `${getAppRoot()}api/dataset_collections/${id}?instance_type=history`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

// There isn't really a good way to know when to stop polling for HDCA updates,
// but we know the populated_state should at least be ok.
export default SingleQueryProvider(getDatasetCollection, (result) => result.populated_state === "ok");
