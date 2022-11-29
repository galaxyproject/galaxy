<template>
    <b-button
        v-b-tooltip.hover.bottom
        :title="title | localize"
        :data-workflow-run="id"
        class="workflow-run btn-sm btn-primary"
        @click.stop="executeWorkflow">
        <FontAwesomeIcon icon="fa-play" />
    </b-button>
</template>

<script>
import { BButton } from "bootstrap-vue";
import { VBTooltip } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlay } from "@fortawesome/free-solid-svg-icons";

library.add(faPlay);

export default {
    components: {
        BButton,
        FontAwesomeIcon,
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
