<template>
    <b-modal v-model="hasTool" :title="modalTitle">
        <div v-if="tool && tool.help.length" v-html="tool.help"></div>
        <p v-else>{{ "Tool help is unavailable for this dataset." | localize }}</p>
    </b-modal>
</template>

<script>
import { loadToolFromJob } from "./model/queries";

export default {
    data() {
        return {
            tool: null,
        };
    },
    computed: {
        modalTitle() {
            return this.tool ? `Tool Help: ${this.tool.name}` : "Tool Help";
        },
        helpHtml() {
            return this.tool ? this.tool.help : "";
        },
        hasTool: {
            get() {
                return Boolean(this.tool);
            },
            set(newVal) {
                this.tool = null;
            },
        },
    },
    methods: {
        async toggleToolHelp(jobId) {
            if (this.tool && this.tool.job_id == jobId) {
                this.closePanel();
            } else {
                this.tool = await loadToolFromJob(jobId);
            }
        },
        closePanel() {
            this.tool = null;
        },
    },
    created() {
        this.eventHub.$on("toggleToolHelp", this.toggleToolHelp);
    },
};
</script>
