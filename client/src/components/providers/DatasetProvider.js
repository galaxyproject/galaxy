import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

import { fetchDatasetDetails } from "@/api/datasets";
import { SingleQueryProvider } from "@/components/providers/SingleQueryProvider";
import { rethrowSimple } from "@/utils/simple-error";

import { stateIsTerminal } from "./utils";

async function getDatasetAttributes({ id }) {
    const url = `${getAppRoot()}dataset/get_edit?dataset_id=${id}`;
    try {
        const { data } = await axios.get(url);
        return data;
    } catch (e) {
        rethrowSimple(e);
    }
}

export const DatasetAttributesProvider = SingleQueryProvider(getDatasetAttributes);
export default SingleQueryProvider(fetchDatasetDetails, stateIsTerminal);
