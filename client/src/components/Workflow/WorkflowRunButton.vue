<template>
    <GButton
        v-b-tooltip.hover.bottom
        :title="title | localize"
        :data-workflow-run="id"
        class="workflow-run btn-sm btn-primary fa fa-play"
        @click.stop="executeWorkflow" />
</template>

<script>
import { VBTooltip } from "bootstrap-vue";
import GButton from "component-library/GButton";

export default {
    components: {
        GButton,
    },
    directives: {
        VBTooltip,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        root: {
            type: String,
            required: true,
        },
    },
    computed: {
        title() {
            return "Run workflow";
        },
    },
    methods: {
        executeWorkflow() {
            window.location.assign(`${this.root}workflows/run?id=${this.id}`);
        },
    },
};
</script>
