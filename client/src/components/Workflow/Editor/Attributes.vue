<template>
    <div id="edit-attributes" class="right-content p-2" itemscope itemtype="http://schema.org/CreativeWork">
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <div id="workflow-name-area">
            <b>Name</b>
            <meta itemprop="name" :content="name" />
            <b-input id="workflow-name" v-model="nameCurrent" @keyup="$emit('update:nameCurrent', nameCurrent)" />
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
                <b-list-group-item v-for="[key, p] in parameters.parameters.entries()" :key="key"
                    >{{ key + 1 }}: {{ p.name }}
                </b-list-group-item>
            </b-list-group>
        </div>
        <div id="workflow-annotation-area" class="mt-2">
            <b>Annotation</b>
            <meta itemprop="description" :content="annotationCurrent" />
            <b-textarea
                id="workflow-annotation"
                v-model="annotationCurrent"
                @keyup="$emit('update:annotationCurrent', annotationCurrent)" />
            <div class="form-text text-muted">These notes will be visible when this workflow is viewed.</div>
        </div>
        <div id="workflow-license-area" class="mt-2">
            <b>License</b>
            <LicenseSelector :input-license="license" @onLicense="onLicense" />
        </div>
        <div id="workflow-creator-area" class="mt-2">
            <b>Creator</b>
            <CreatorEditor :creators="creatorAsList" @onCreators="onCreator" />
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
import { format } from "date-fns";
import { Services } from "components/Workflow/services";
import Tags from "components/Common/Tags";
import LicenseSelector from "components/License/LicenseSelector";
import CreatorEditor from "components/SchemaOrg/CreatorEditor";
import { UntypedParameters } from "./modules/parameters";

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
            default: null,
        },
        tags: {
            type: Array,
            required: true,
        },
        annotation: {
            type: String,
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
            type: UntypedParameters,
            default: null,
        },
    },
    data() {
        return {
            message: null,
            messageVariant: null,
            tagsCurrent: this.tags,
            versionCurrent: this.version,
            annotationCurrent: this.annotation,
            nameCurrent: this.name,
        };
    },
    computed: {
        creatorAsList() {
            let creator = this.creator;
            if (!creator) {
                creator = [];
            } else if (!(creator instanceof Array)) {
                creator = [creator];
            }
            return creator;
        },
        hasParameters() {
            return this.parameters && this.parameters.parameters.length > 0;
        },
        versionOptions() {
            const versions = [];
            for (let i = 0; i < this.versions.length; i++) {
                const current_wf = this.versions[i];
                let update_time;
                if (current_wf.update_time) {
                    update_time = `${format(Date.parse(current_wf.update_time), "MMM do yyyy")}, `;
                } else {
                    update_time = "";
                }
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
        annotation() {
            this.annotationCurrent = this.annotation;
        },
        name() {
            this.nameCurrent = this.name;
        },
    },
    created() {
        this.services = new Services();
    },
    methods: {
        onTags(tags) {
            this.tagsCurrent = tags;
            this.onAttributes({ tags });
        },
        onVersion() {
            this.$emit("onVersion", this.versionCurrent);
        },
        onLicense(license) {
            this.$emit("onLicense", license);
        },
        onCreator(creator) {
            this.$emit("onCreator", creator);
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
