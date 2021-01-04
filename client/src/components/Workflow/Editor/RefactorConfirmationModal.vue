<template>
    <b-modal v-model="show" :title="title" scrollable ok-only ok-title="Save">
        <div class="workflow-refactor-modal"></div>
    </b-modal>
</template>

<script>
import { refactor } from "./modules/services";
import { BModal } from "bootstrap-vue";

export default {
    components: { BModal },
    props: {
        refactorActions: {
            type: Array,
            required: true,
        },
        workflowId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            show: this.refactorActions.length > 0,
        };
    },
    watch: {
        refactorActions() {
            if (this.refactorActions.length > 0) {
                this.dryRun();
            }
        },
    },
    methods: {
        dryRun() {
            this.$emit("onWorkflowMessage", "Pre-checking requested workflow changes (dry run)...", "progress");
            refactor(this.workflowId, this.refactorActions, true) // dry run
                .then((data) => {
                    // TODO: render in the confirmation dialog above if there are
                    // any messages.
                    this.$emit("onWorkflowMessage", "Applying requested workflow changes...", "progress");
                    refactor(this.workflowId, this.refactorActions)
                        .then((data) => {
                            this.$emit("onRefactor", data);
                        })
                        .catch(this.onError);
                })
                .catch(this.onError);
        },
        onError(response) {
            this.$emit("onWorkflowError", "Reworking workflow failed...", response);
        },
    },
};
</script>
