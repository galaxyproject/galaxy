<template>
    <div class="tools" :title="title">
        <span v-if="toolIds.length == 1">
            <tool-display :tool-id="toolIds[0]" />
        </span>
        <span v-else-if="compact"> {{ toolIds.length }} tools </span>
        <div v-else :key="index" v-for="(toolId, index) in toolIds">
            <tool-display :tool-id="toolId" />
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
            required: true
        },
        compact: {
            type: Boolean,
            default: true
        }
    },
    computed: {
        title: function() {
            return this.compact ? this.toolIds.join(", ") : "";
        }
    }
};
</script>
