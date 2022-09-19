<template>
    <b-modal v-model="show" :title="title" scrollable ok-title="Save" @ok="executeRefactoring">
        <div class="workflow-refactor-modal">
            {{ message }}
            <ul>
                <li v-for="(actionExecution, executionIndex) in confirmActionExecutions" :key="executionIndex">
                    <ul>
                        <li v-for="(actionMessage, messageIndex) in actionExecution.messages" :key="messageIndex">
                            - {{ actionMessage.message }}
                        </li>
                    </ul>
                </li>
            </ul>
        </div>
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
        title: {
            type: String,
            default: "Issues reworking this workflow",
        },
        message: {
            type: String,
            default: "Please review the following potential issues...",
        },
    },
    data() {
        return {
            show: this.refactorActions.length > 0,
            confirmActionExecutions: [],
        };
    },
    watch: {
        refactorActions() {
            if (this.refactorActions.length > 0) {
                this.dryRun();
            }
        },
        show() {
            if (this.show) {
                // emit that this is showing, so the workflow editor
                // can hide modal.
                this.$emit("onShow");
            }
        },
    },
    methods: {
        dryRun() {
            this.$emit("onWorkflowMessage", "Pre-checking requested workflow changes (dry run)...", "progress");
            refactor(this.workflowId, this.refactorActions, true) // dry run
                .then(this.onDryRunResponse)
                .catch(this.onError);
        },
        onError(response) {
            this.$emit("onWorkflowError", "Reworking workflow failed...", response);
        },
        onDryRunResponse(data) {
            let anyRequireConfirmation = false;
            for (const actionExecution of data.action_executions) {
                if (actionExecution.messages.length > 0) {
                    anyRequireConfirmation = true;
                }
            }
            if (anyRequireConfirmation) {
                this.show = true;
                this.confirmActionExecutions = data.action_executions;
            } else {
                this.executeRefactoring();
            }
        },
        executeRefactoring() {
            this.show = false;
            this.$emit("onWorkflowMessage", "Applying requested workflow changes...", "progress");
            refactor(this.workflowId, this.refactorActions)
                .then((data) => {
                    this.$emit("onRefactor", data);
                })
                .catch(this.onError);
        },
    },
};
</script>
