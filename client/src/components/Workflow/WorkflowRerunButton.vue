<template>
    <b-button
        v-b-tooltip.hover.bottom
        :title="title | localize"
        :data-workflow-run="workflowId"
        class="workflow-run btn-sm btn-primary fa fa-repeat"
        @click.stop="rerunInvocation" />
</template>

<script>
import { BButton } from "bootstrap-vue";
import { VBTooltip } from "bootstrap-vue";

// todo: write test
export default {
    components: {
        BButton,
    },
    directives: {
        VBTooltip,
    },
    props: {
        workflowId: {
            type: String,
            required: true,
        },
        invocationId: {
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
            return "Rerun invocation";
        },
    },
    methods: {
        rerunInvocation() {
            window.location.assign(
                `${this.root}workflows/run?workflow_id=${this.workflowId}&invocation_id=${this.invocationId}`
            );
        },
    },
};
</script>
