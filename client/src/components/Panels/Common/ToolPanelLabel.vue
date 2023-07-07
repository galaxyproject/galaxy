<template>
    <div v-b-tooltip.topright.hover class="tool-panel-label" :title="description">
        {{ definition.text }}
        <ToolPanelLinks :links="definition.links" />
    </div>
</template>

<script>
import ToolPanelLinks from "./ToolPanelLinks";

export default {
    components: { ToolPanelLinks },
    props: {
        definition: {
            type: Object,
            required: true,
        },
    },
    computed: {
        description() {
            return this.definition.description;
        },
    },
};
</script>

<style scoped lang="scss">
.tool-panel-label {
    &:deep(.tool-panel-links) {
        display: none;
    }

    &:hover:deep(.tool-panel-links) {
        display: inline;
    }
}
</style>
