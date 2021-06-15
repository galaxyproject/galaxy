import { default as RxProviderMixin } from "./rxProviders";
import { datasetMonitor } from "./monitors";

export default {
    mixins: [RxProviderMixin],
    methods: {
        buildMonitor() {
            return datasetMonitor();
        },
    },
};
