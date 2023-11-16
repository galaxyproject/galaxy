<template>
    <BButton
        v-b-tooltip.hover.bottom
        :title="title | localize"
        :data-workflow-run="id"
        :disabled="clicked"
        class="workflow-run btn-sm btn-primary fa fa-play"
        @click.stop="executeWorkflow" />
</template>

<script>
import { BButton, VBTooltip } from "bootstrap-vue";

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
    data() {
        return{
            clicked: false,
        }
    },
    computed: {
        title() {
            return "Run workflow";
        },
    },
    methods: {
        executeWorkflow() {
            this.clicked = true;
            this.$router.push(`/workflows/run?id=${this.id}`);
        },
    },
};
</script>
