import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { rethrowSimple } from "utils/simple-error";

async function datasetAttributes({ id }) {
    const url = `${getAppRoot()}dataset/get_edit?dataset_id=${id}`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export const DatasetAttributesProvider = SingleQueryProvider(datasetAttributes);
