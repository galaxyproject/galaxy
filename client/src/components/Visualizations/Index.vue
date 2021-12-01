<template>
    <div>
        <PluginList :dataset-id="datasetId" />
    </div>
</template>
<script>
import DisplayApplications from "./DisplayApplications";
import PluginList from "./PluginList";
export default {
    components: {
        PluginList,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
};
</script>
