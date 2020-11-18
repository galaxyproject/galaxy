<template>
    <div id="edit-attributes" class="right-content p-2" itemscope itemtype="http://schema.org/CreativeWork">
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <div id="workflow-name-area">
            <b>Name</b>
            <meta itemprop="name" :content="name" />
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
            <meta itemprop="description" :content="annotation" />
            <b-textarea id="workflow-annotation" :value="annotation" @input="onAnnotation" />
            <div class="form-text text-muted">
                These notes will be visible when this workflow is viewed.
            </div>
        </div>
        <div id="workflow-license-area" class="mt-2">
            <b>License</b>
            <LicenseSelector :inputLicense="licenseCurrent" @onLicense="onLicense" />
        </div>
        <div id="workflow-creator-area" class="mt-2">
            <b>Creator</b>
            <CreatorEditor :creators="creatorCurrent" @onCreators="onCreator" />
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
import moment from "moment";
import { Services } from "components/Workflow/services";
import Tags from "components/Common/Tags";
import LicenseSelector from "components/License/LicenseSelector";
import CreatorEditor from "components/SchemaOrg/CreatorEditor";

Vue.use(BootstrapVue);

export default {
    name: "Attributes",
    components: {
        Tags,
        LicenseSelector,
        CreatorEditor,
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
        license: {
            type: String,
            default: "",
        },
        creator: {
            default: null,
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
        let creator = this.creator;
        if (!creator) {
            creator = [];
        } else if (!(creator instanceof Array)) {
            creator = [creator];
        }
        return {
            message: null,
            messageVariant: null,
            licenseCurrent: this.license,
            tagsCurrent: this.tags,
            versionCurrent: this.version,
            creatorCurrent: creator,
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
                const update_time = moment.utc(current_wf.update_time).format("MMM Do YYYY");
                const label = `${current_wf.version + 1}: ${update_time}, ${current_wf.steps} steps`;
                versions.push({
                    version: i,
                    label: label,
                });
            }
            return versions;
        },
    },
    watch: {
        version() {
            this.versionCurrent = this.version;
        },
        license() {
            this.licenseCurrent = this.license;
        },
        creator() {
            let creator = this.creator;
            if (!creator) {
                creator = [];
            } else if (!(creator instanceof Array)) {
                creator = [creator];
            }
            this.creatorCurrent = creator;
        },
    },
    methods: {
        onTags(tags) {
            this.tagsCurrent = tags;
            this.onAttributes({ tags });
        },
        onAnnotation(annotation) {
            if (this.annotationTimeout) {
                clearTimeout(this.annotationTimeout);
            }
            this.annotationTimeout = setTimeout(() => {
                this.onAttributes({ annotation });
            }, 300);
        },
        onRename(name) {
            this.onAttributes({ name });
            this.$emit("onRename", name);
        },
        onVersion() {
            this.$emit("onVersion", this.versionCurrent);
        },
        onLicense(license) {
            this.licenseCurrent = license;
            this.onAttributes({ license });
            this.$emit("onLicense", this.licenseCurrent);
        },
        onCreator(creator) {
            this.creatorCurrent = creator;
            this.onAttributes({ creator });
            this.$emit("onCreator", this.creatorCurrent);
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
        beforeDestroy: function () {
            clearTimeout(this.annotationTimeout);
        },
    },
};
</script>
