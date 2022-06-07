<template>
    <b-button
        v-b-tooltip.hover.bottom
        :title="title | localize"
        :data-workflow-run="id"
        class="workflow-run btn-sm btn-primary fa fa-play"
        @click.stop="executeWorkflow" />
</template>

<script>
import { BButton } from "bootstrap-vue";
import { VBTooltip } from "bootstrap-vue";

export default {
    components: {
        BButton,
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
