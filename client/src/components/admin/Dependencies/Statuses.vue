<template>
    <span class="dependency-statuses">
        <b v-if="statuses.length == 0"> <span class="fa fa-times text-danger"></span><i>未解析</i> </b>
        <span v-else-if="merged">
            <StatusDisplay :status="statuses[0]" :all-statuses="statuses" />
        </span>
        <div v-for="(item_status, index) in statuses" v-else :key="index">
            <StatusDisplay :status="item_status" />
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
