import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { rethrowSimple } from "utils/simple-error";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";

async function getDatasetCollection({ id }) {
    const url = `${getAppRoot()}api/dataset_collections/${id}?instance_type=history`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export default SingleQueryProvider(getDatasetCollection);
