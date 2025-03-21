<template>
    <BModal v-model="show" :title="title" scrollable ok-title="保存" @ok="executeRefactoring">
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
    </BModal>
</template>

<script>
import { BModal } from "bootstrap-vue";

import { refactor } from "./modules/services";

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
            default: "重新处理此工作流的问题",
        },
        message: {
            type: String,
            default: "请查看以下潜在问题...",
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
            this.$emit("onWorkflowMessage", "预检查请求的工作流更改（干运行）...", "progress");
            refactor(this.workflowId, this.refactorActions, true) // dry run
                .then(this.onDryRunResponse)
                .catch(this.onError);
        },
        onError(response) {
            this.$emit("onWorkflowError", "重新处理工作流失败...", response);
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
            this.$emit("onWorkflowMessage", "应用请求的工作流更改...", "progress");
            refactor(this.workflowId, this.refactorActions)
                .then((data) => {
                    this.$emit("onRefactor", data);
                })
                .catch(this.onError);
        },
    },
};
</script>
