<template>
    <div class="tools" :title="title">
        <span v-if="toolIds.length == 1">
            <ToolDisplay :tool-id="toolIds[0]" />
        </span>
        <span v-else-if="compact"> {{ toolIds.length }} 个工具 </span>
        <div v-for="(toolId, index) in toolIds" v-else :key="index">
            <ToolDisplay :tool-id="toolId" />
        </div>
    </div>
</template>
<script>
import ToolDisplay from "./ToolDisplay";

export default {
    components: { ToolDisplay },
    props: {
        toolIds: {
            type: Array,
            required: true,
        },
        compact: {
            type: Boolean,
            default: true,
        },
    },
    computed: {
        title: function () {
            return this.compact ? this.toolIds.join(", ") : "";
        },
    },
};
</script>
