<template>
    <div
        v-b-tooltip.topright.hover
        class="tool-panel-label"
        :title="description"
        @mouseover="hover = true"
        @mouseleave="hover = false">
        {{ definition.text }}
        <ToolPanelLinks :show="hover" :links="definition.links" />
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
    data() {
        return {
            hover: false,
        };
    },
    computed: {
        description() {
            return this.definition.description;
        },
    },
};
</script>
