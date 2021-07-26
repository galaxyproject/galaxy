import { default as RxProviderMixin } from "./rxProviders";
import { datasetCollectionMonitor } from "./monitors";

export default {
    mixins: [RxProviderMixin],
    methods: {
        buildMonitor() {
            return datasetCollectionMonitor();
        },
    },
};
