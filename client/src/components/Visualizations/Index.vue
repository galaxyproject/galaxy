<template>
    <div>
        <DisplayApplications v-if="datasetId" :dataset-id="datasetId" />
        <PluginList :dataset-id="datasetId" />
    </div>
</template>
<script>
import DisplayApplications from "./DisplayApplications";
import PluginList from "./PluginList";
export default {
    components: {
        PluginList,
        DisplayApplications,
    },
    props: {
        datasetId: {
            type: String,
            default: null,
        },
    },
};
</script>
