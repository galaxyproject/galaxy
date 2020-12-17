<template>
    <component :is="summaryComponent" :dataset="dataset" class="summary" />
</template>

<script>
import { capitalize, camelize } from "underscore.string";

import Discarded from "./Discarded";
import Empty from "./Empty";
import Error from "./Error";
import New from "./New";
import NotViewable from "./NotViewable";
import Ok from "./Ok";
import Paused from "./Paused";
import Queued from "./Queued";
import Running from "./Running";
import SettingMetadata from "./SettingMetadata";
import Upload from "./Upload";

export default {
    inject: ["STATES"],
    components: {
        Discarded,
        Empty,
        Error,
        New,
        NotViewable,
        Ok,
        Paused,
        Queued,
        Running,
        SettingMetadata,
        Upload,
    },
    props: {
        dataset: { type: Object, required: true },
    },
    computed: {
        summaryComponent() {
            let state = this.dataset.state;
            if (state == this.STATES.FAILED_METADATA) {
                state = this.STATES.OK;
            }
            return capitalize(camelize(state));
        },
    },
};
</script>
