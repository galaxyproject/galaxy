<template>
    <b-card body-class="p-0">
        <b-card-header v-if="!embedded">
            <span class="float-right">
                <b-button
                    v-b-tooltip.hover
                    :href="downloadUrl"
                    variant="link"
                    size="sm"
                    role="button"
                    title="Download Workflow"
                    type="button"
                    class="py-0 px-1"
                    data-description="workflow download">
                    <span class="fa fa-download" />
                </b-button>
                <b-button
                    v-b-tooltip.hover
                    :href="importUrl"
                    role="button"
                    variant="link"
                    title="Import Workflow"
                    type="button"
                    class="py-0 px-1"
                    data-description="workflow import">
                    <span class="fa fa-file-import" />
                </b-button>
            </span>
            <span>
                <span>Workflow:</span>
                <span class="font-weight-light" data-description="workflow name">{{ workflowName }}</span>
            </span>
        </b-card-header>
        <b-card-body>
            <LoadingSpan v-if="loading" message="Loading Workflow" />
            <div v-else :class="!expanded && 'content-height'">
                <div v-for="step in itemContent.steps" :key="step.order_index" class="mb-2">
                    <div>Step {{ step.order_index + 1 }}: {{ step.label }}</div>
                    <WorkflowTree :input="step" :skip-head="true" />
                </div>
            </div>
        </b-card-body>
    </b-card>
</template>

<script>
import { withPrefix } from "utils/redirect";
import { urlData } from "utils/url";
import LoadingSpan from "components/LoadingSpan";
import WorkflowTree from "./WorkflowTree";
export default {
    components: {
        LoadingSpan,
        WorkflowTree,
    },
    props: {
        args: {
            type: Object,
            required: true,
        },
        embedded: {
            type: Boolean,
            default: false,
        },
        expanded: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            itemContent: null,
            loading: true,
        };
    },
    computed: {
        workflowName() {
            return this.itemContent ? this.itemContent.name : "...";
        },
        downloadUrl() {
            return withPrefix(`/api/workflows/${this.args.workflow_id}/download?format=json-download`);
        },
        importUrl() {
            return withPrefix(`/workflow/imp?id=${this.args.workflow_id}`);
        },
        itemUrl() {
            return `/api/workflows/${this.args.workflow_id}/download?style=preview`;
        },
    },
    created() {
        const url = this.itemUrl;
        urlData({ url }).then((data) => {
            this.itemContent = data;
            this.loading = false;
        });
    },
};
</script>
<style scoped>
.content-height {
    max-height: 15rem;
    overflow-y: auto;
}
</style>
