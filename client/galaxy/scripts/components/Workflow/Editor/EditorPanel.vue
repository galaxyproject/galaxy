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
                    <b-input id="workflow-name" :value="name" @change="onRename" />
                </div>
                <div id="workflow-version-area" class="mt-2">
                    <b>Version</b>
                    <b-form-select v-model="versionCurrent" @change="onVersion">
                        <b-form-select-option v-for="v in versionOptions" :key="v.version" :value="v.version">
                            {{ v.label }}
                        </b-form-select-option>
                    </b-form-select>
                </div>
                <div id="workflow-annotation-area" class="mt-2">
                    <b>Annotation</b>
                    <b-textarea id="workflow-annotation" :value="annotation" @change="onAnnotation" />
                    <div class="form-text text-muted">
                        These notes will be visible when this workflow is viewed.
                    </div>
                </div>
                <div class="mt-2">
                    <b>Tags</b>
                    <Tags :tags="tags" @input="onTags" />
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
            messageVariant: null,
            versionCurrent: this.version
        };
    },
    props: {
        id: {
            type: String,
            required: true
        },
        name: {
            type: String,
            required: true
        },
        tags: {
            type: Array,
            required: true
        },
        annotation: {
            type: String
        },
        version: {
            type: Number
        },
        versions: {
            type: Array
        }
    },
    created() {
        this.services = new Services();
    },
    computed: {
        versionOptions() {
            const versions = [];
            for (let i = 0; i < this.versions.length; i++) {
                const current_wf = this.versions[i];
                let label = `Version ${current_wf.version}, ${current_wf.steps} steps`;
                if (i == this.version) {
                    label = `${label} (active)`;
                }
                versions.push({
                    version: i,
                    label: label
                });
            }
            return versions;
        }
    },
    methods: {
        onTags(tags) {
            this.tags = tags;
            this.services
                .updateWorkflow(this.id, {
                    tags: this.tags
                })
                .catch(error => {
                    this.onError(error);
                });
        },
        onAnnotation(annotation) {
            this.services.updateWorkflow(this.id, { annotation }).catch(error => {
                this.onError(error);
            });
        },
        onRename(name) {
            this.services.updateWorkflow(this.id, { name }).catch(error => {
                this.onError(error);
            });
        },
        onVersion(version) {
            this.$emit("onVersion", this.versionCurrent);
        },
        onError: function(message) {
            this.message = message;
            this.messageVariant = "danger";
        }
    }
};
</script>
