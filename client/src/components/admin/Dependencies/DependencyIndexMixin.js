import { getAppRoot } from "@/onload/loadConfig";

import ContainerDescription from "./ContainerDescription.vue";
import ContainerResolver from "./ContainerResolver.vue";
import DependencyIndexWrapper from "./DependencyIndexWrapper.vue";
import DependencyResolver from "./DependencyResolver.vue";
import Requirements from "./Requirements.vue";
import StatusDisplay from "./StatusDisplay.vue";
import Statuses from "./Statuses.vue";
import ToolDisplay from "./ToolDisplay.vue";
import Tools from "./Tools.vue";

export default {
    components: {
        ContainerDescription,
        ContainerResolver,
        DependencyIndexWrapper,
        DependencyResolver,
        Requirements,
        StatusDisplay,
        Statuses,
        ToolDisplay,
        Tools,
    },
    created() {
        this.root = getAppRoot();
        this.load();
    },
    computed: {
        hasSelection: function () {
            // Not reactive yet...
            for (const item of this.items) {
                if (item["selected"]) {
                    return true;
                }
            }
            return false;
        },
    },
    methods: {
        showRowDetails(row, index, e) {
            if (e.target.nodeName != "A") {
                row._showDetails = !row._showDetails;
            }
        },
        handleError(e) {
            this.error = e;
        },
    },
};
