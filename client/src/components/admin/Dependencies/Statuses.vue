<template>
    <span class="dependency-statuses">
        <b v-if="statuses.length == 0">
            <FontAwesomeIcon icon="fa-times" class="text-danger"></FontAwesomeIcon><i>unresolved</i>
        </b>
        <span v-else-if="merged">
            <status-display :status="statuses[0]" :all-statuses="statuses" />
        </span>
        <div v-for="(item_status, index) in statuses" v-else :key="index">
            <status-display :status="item_status" />
        </div>
    </span>
</template>
<script>
import StatusDisplay from "./StatusDisplay";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";

library.add(faTimes);

export default {
    components: { StatusDisplay, FontAwesomeIcon },
    props: {
        statuses: {
            type: Array,
            required: true,
        },
        compact: {
            type: Boolean,
            default: true,
        },
    },
    computed: {
        merged: function () {
            return this.statuses.length >= 1 && this.statuses[0].model_class == "MergedCondaDependency";
        },
    },
};
</script>
