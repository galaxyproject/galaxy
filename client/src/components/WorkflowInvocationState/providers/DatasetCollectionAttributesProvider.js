import { default as RxProviderMixin } from "./rxProviders";
import { datasetCollectionAttributesMonitor } from "./monitors";

export default {
    mixins: [RxProviderMixin],
    methods: {
        buildMonitor() {
            return datasetCollectionAttributesMonitor();
        },
    },
};
