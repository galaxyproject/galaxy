<template>
    <div v-b-tooltip.topright.hover.noninteractive class="tool-panel-label" tabindex="0" :title="description">
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

    &:hover,
    &:focus,
    &:focus-within {
        &:deep(.tool-panel-links) {
            display: inline;
        }
    }
}
</style>
