<template>
    <div id="edit-attributes" class="right-content p-2">
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
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
        <div v-if="hasParameters" id="workflow-parameters-area" class="mt-2">
            <b>Parameters</b>
            <b-list-group>
                <b-list-group-item v-for="[key, p] in parameters.entries()" :key="key"
                    >{{ key + 1 }}: {{ p }}
                </b-list-group-item>
            </b-list-group>
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
            <Tags :tags="tagsCurrent" @input="onTags" />
            <div class="form-text text-muted">
                Apply tags to make it easy to search for and find items with the same tag.
            </div>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services } from "components/Workflow/services";
import Tags from "components/Common/Tags";

Vue.use(BootstrapVue);

export default {
    name: "Attributes",
    components: {
        Tags,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        name: {
            type: String,
            required: true,
        },
        tags: {
            type: Array,
            required: true,
        },
        annotation: {
            type: String,
            default: "",
        },
        version: {
            type: Number,
            default: null,
        },
        versions: {
            type: Array,
            default: null,
        },
        parameters: {
            type: Array,
            default: null,
        },
    },
    data() {
        return {
            message: null,
            messageVariant: null,
            tagsCurrent: this.tags,
            versionCurrent: this.version,
        };
    },
    created() {
        this.services = new Services();
    },
    computed: {
        hasParameters() {
            return this.parameters.length > 0;
        },
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
                    label: label,
                });
            }
            return versions;
        },
    },
    methods: {
        onTags(tags) {
            this.tagsCurrent = tags;
            this.onAttributes({ tags });
        },
        onAnnotation(annotation) {
            this.onAttributes({ annotation });
        },
        onRename(name) {
            this.onAttributes({ name });
            this.$emit("onRename", name);
        },
        onVersion() {
            this.$emit("onVersion", this.versionCurrent);
        },
        onError(error) {
            this.message = error;
            this.messageVariant = "danger";
        },
        onAttributes(data) {
            this.services.updateWorkflow(this.id, data).catch((error) => {
                this.onError(error);
            });
        },
    },
};
</script>
