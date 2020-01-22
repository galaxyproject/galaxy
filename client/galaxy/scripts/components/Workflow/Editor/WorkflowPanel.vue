<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-text">Details</div>
            </div>
        </div>
        <div class="unified-panel-body workflow-right">
            <b-alert class="m-2" :variant="messageVariant" :show="!!message">
                {{ message }}
            </b-alert>
            <div id="edit-attributes" class="right-content p-2">
                <div id="workflow-name-area">
                    <b>Name</b>
                    <b-input id="workflow-name" :value="workflow.name" @change="onRename" />
                </div>
                <div id="workflow-version-area" class="mt-2">
                    <b>Version</b>
                    <select id="workflow-version-switch" class="ui-input"
                        >Select version</select
                    >
                </div>
                <div id="workflow-annotation-area" class="mt-2">
                    <b>Annotation</b>
                    <b-textarea id="workflow-annotation" :value="workflow.annotation" @change="onAnnotation" />
                    <div class="form-text text-muted">
                        These notes will be visible when this workflow is viewed.
                    </div>
                </div>
                <div class="mt-2">
                    <b>Tags</b>
                    <Tags :item="workflow" @input="onTags" />
                    <div class="form-text text-muted">
                        Apply tags to make it easy to search for and find items with the same tag.
                    </div>
                </div>
            </div>
            <div id="right-content" class="right-content" />
        </div>
    </div>
</template>

<script>
import Tags from "components/Common/Tags";
import { Services } from "components/Workflow/services";
export default {
    name: "EditorPanel",
    components: {
        Tags
    },
    data() {
        return {
            message: null,
            messageVariant: null
        };
    },
    props: {
        workflow: {
            type: Object,
            required: true
        }
    },
    created() {
        this.services = new Services();
    },
    methods: {
        onTags(workflow) {
            this.services
                .updateWorkflow(workflow.id, {
                    tags: workflow.tags
                })
                .catch(error => {
                    this.onError(error);
                });
        },
        onAnnotation(annotation) {
            this.services.updateWorkflow(this.workflow.id, { annotation }).catch(error => {
                this.onError(error);
            });
        },
        onRename(name) {
            this.services.updateWorkflow(this.workflow.id, { name }).catch(error => {
                this.onError(error);
            });
        },
        onError: function(message) {
            this.message = message;
            this.messageVariant = "danger";
        }
    }
};
</script>
