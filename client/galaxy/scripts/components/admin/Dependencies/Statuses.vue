<template>
    <span class="dependency-statuses">
        <b v-if="statuses.length == 0"> <span class="fa fa-times text-danger"></span><i>unresolved</i> </b>
        <span v-else-if="merged">
            <status-display :status="statuses[0]" :all-statuses="statuses" />
        </span>
        <div v-else :key="index" v-for="(item_status, index) in statuses">
            <status-display :status="item_status" />
        </div>
    </span>
</template>
<script>
import StatusDisplay from "./StatusDisplay";

export default {
    components: { StatusDisplay },
    props: {
        statuses: {
            type: Array,
            required: true
        },
        compact: {
            type: Boolean,
            default: true
        }
    },
    computed: {
        merged: function() {
            return this.statuses.length >= 1 && this.statuses[0].model_class == "MergedCondaDependency";
        }
    }
};
</script>
