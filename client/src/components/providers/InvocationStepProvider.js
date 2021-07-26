import { default as RxProviderMixin } from "./rxProviders";
import { invocationStepMonitor } from "./monitors";

export default {
    mixins: [RxProviderMixin],
    methods: {
        buildMonitor() {
            return invocationStepMonitor();
        },
    },
};
