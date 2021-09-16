import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { SingleQueryProvider } from "components/providers/SingleQueryProvider";
import { default as RxProviderMixin } from "./rxProviders";
import { datasetMonitor } from "./monitors";
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
export default {
    mixins: [RxProviderMixin],
    methods: {
        buildMonitor() {
            return datasetMonitor();
        },
    },
};
