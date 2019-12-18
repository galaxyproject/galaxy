import { getAppRoot } from "onload/loadConfig";
import DependencyIndexWrapper from "./DependencyIndexWrapper";
import DependencyResolver from "./DependencyResolver";
import Requirements from "./Requirements";
import StatusDisplay from "./StatusDisplay";
import Statuses from "./Statuses";
import ContainerDescription from "./ContainerDescription";
import ContainerResolver from "./ContainerResolver";
import Tools from "./Tools";
import ToolDisplay from "./ToolDisplay";

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
        Tools
    },
    created() {
        this.root = getAppRoot();
        this.load();
    },
    computed: {
        hasSelection: function() {
            // Not reactive yet...
            for (const item of this.items) {
                if (item["selected"]) {
                    return true;
                }
            }
            return false;
        }
    },
    methods: {
        showRowDetails(row, index, e) {
            if (e.target.nodeName != "A") {
                row._showDetails = !row._showDetails;
            }
        },
        handleError(e) {
            this.error = e;
        }
    }
};
