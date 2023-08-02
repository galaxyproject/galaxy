<template>
    <GButton
        v-b-tooltip.hover.bottom
        :title="title | localize"
        :data-workflow-run="id"
        class="workflow-run btn-sm btn-primary fa fa-play"
        @click.stop="executeWorkflow" />
</template>

<script>
import { GButton } from "@/component-library";

export default {
    components: {
        GButton,
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
