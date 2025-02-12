<template>
    <ActivityPanel id="edit-attributes" title="Attributes" itemscope itemtype="http://schema.org/CreativeWork">
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <div id="workflow-name-area">
            <b>Name</b>
            <meta itemprop="name" :content="name" />
            <b-input
                id="workflow-name"
                v-model="nameCurrent"
                :state="!nameCurrent ? false : null"
                @keyup="$emit('update:nameCurrent', nameCurrent)" />
        </div>
        <div v-if="versionOptions.length > 0" id="workflow-version-area" class="mt-2">
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
        <div
            id="workflow-annotation-area"
            class="mt-2"
            :class="{ 'bg-secondary': showAnnotationHightlight, 'highlight-attribute': showAnnotationHightlight }">
            <b>Short Description</b>
            <meta itemprop="description" :content="annotationCurrent" />
            <b-textarea
                id="workflow-annotation"
                v-model="annotationCurrent"
                @keyup="$emit('update:annotationCurrent', annotationCurrent)" />
            <div class="form-text text-muted">
                This short description will be visible when this workflow is viewed and should be limited to a sentence
                or two.
            </div>
            <b-popover
                custom-class="best-practice-popover"
                target="workflow-annotation"
                boundary="window"
                placement="right"
                :show.sync="showAnnotationHightlight"
                triggers="manual"
                title="Best Practice"
                :content="bestPracticeWarningAnnotation">
            </b-popover>
        </div>
        <div
            id="workflow-license-area"
            class="mt-2"
            :class="{ 'bg-secondary': showLicenseHightlight, 'highlight-attribute': showLicenseHightlight }">
            <b>License</b>
            <LicenseSelector id="license-selector" :input-license="license" @onLicense="onLicense" />
            <b-popover
                custom-class="best-practice-popover"
                target="license-selector"
                boundary="window"
                placement="right"
                :show.sync="showLicenseHightlight"
                triggers="manual"
                title="Best Practice"
                :content="bestPracticeWarningLicense">
            </b-popover>
        </div>
        <div
            id="workflow-creator-area"
            class="mt-2"
            :class="{ 'bg-secondary': showCreatorHightlight, 'highlight-attribute': showCreatorHightlight }">
            <b>Creator</b>
            <CreatorEditor id="creator-editor" :creators="creatorAsList" @onCreators="onCreator" />
            <b-popover
                custom-class="best-practice-popover"
                target="creator-editor"
                boundary="window"
                placement="right"
                :show.sync="showCreatorHightlight"
                triggers="manual"
                title="Best Practice"
                :content="bestPracticeWarningCreator">
            </b-popover>
        </div>
        <div class="mt-2">
            <b>Tags</b>
            <StatelessTags :value="tags" @input="onTags" />
            <div class="form-text text-muted">
                Apply tags to make it easy to search for and find items with the same tag.
            </div>
        </div>
        <div class="mt-2">
            <b>Readme</b>
            <b-textarea
                id="workflow-readme"
                v-model="readmeCurrent"
                @keyup="$emit('update:readmeCurrent', readmeCurrent)" />
            <div class="form-text text-muted">
                A detailed description of what the workflow does. It is best to include descriptions of what kinds of
                data are required. Researchers looking for the workflow will see this text. Markdown is enabled.
            </div>
        </div>
        <div class="mt-2">
            <b>Help</b>
            <b-textarea id="workflow-help" v-model="helpCurrent" @keyup="$emit('update:helpCurrent', helpCurrent)" />
            <div class="form-text text-muted">
                A detailed description of how to use the workflow and debug problems with it. Researchers running this
                workflow will see this text. Markdown is enabled.
            </div>
        </div>
        <div class="mt-2">
            <b>Logo URL</b>
            <b-input
                id="workflow-logo-url"
                v-model="logoUrlCurrent"
                @keyup="$emit('update:logoUrlCurrent', logoUrlCurrent)" />
            <div class="form-text text-muted">
                An logo image used when generating publication artifacts for your workflow. This is completely optional.
            </div>
        </div>
    </ActivityPanel>
</template>

<script>
import { format, parseISO } from "date-fns";

import { Services } from "@/components/Workflow/services";

import {
    bestPracticeWarningAnnotation,
    bestPracticeWarningCreator,
    bestPracticeWarningLicense,
} from "./modules/linting";
import { UntypedParameters } from "./modules/parameters";

import LicenseSelector from "@/components/License/LicenseSelector.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import CreatorEditor from "@/components/SchemaOrg/CreatorEditor.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

const bestPracticeHighlightTime = 10000;

export default {
    name: "WorkflowAttributes",
    components: {
        StatelessTags,
        LicenseSelector,
        CreatorEditor,
        ActivityPanel,
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
        highlight: {
            type: String,
            default: null,
        },
        tags: {
            type: Array,
            required: true,
        },
        annotation: {
            type: String,
            default: null,
        },
        license: {
            type: String,
            default: "",
        },
        creator: {
            type: Array,
            default: null,
        },
        logoUrl: {
            type: String,
            default: null,
        },
        readme: {
            type: String,
            default: null,
        },
        help: {
            type: String,
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
            bestPracticeWarningAnnotation: bestPracticeWarningAnnotation,
            bestPracticeWarningCreator: bestPracticeWarningCreator,
            bestPracticeWarningLicense: bestPracticeWarningLicense,
            message: null,
            messageVariant: null,
            versionCurrent: this.version,
            annotationCurrent: this.annotation,
            nameCurrent: this.name,
            logoUrlCurrent: this.logoUrl,
            readmeCurrent: this.readme,
            helpCurrent: this.help,
            showAnnotationHightlight: false,
            showLicenseHightlight: false,
            showCreatorHightlight: false,
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
                    update_time = `${format(
                        parseISO(current_wf.update_time, "yyyy-MM-dd", new Date()),
                        "MMM do yyyy"
                    )}`;
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
        readme() {
            this.readmeCurrent = this.readme;
        },
        help() {
            this.helpCurrent = this.help;
        },
        logoUrl() {
            this.logoUrlCurrent = this.logoUrl;
        },
        highlight: {
            immediate: true,
            handler(newHighlight, oldHighlight) {
                if (newHighlight == oldHighlight) {
                    return;
                }
                if (newHighlight == "annotation") {
                    this.showAnnotationHightlight = true;
                    this.showCreatorHightlight = false;
                    this.showLicenseHightlight = false;
                    this.showReadmeHightlight = false;
                    setTimeout(() => {
                        this.showAnnotationHightlight = false;
                    }, bestPracticeHighlightTime);
                } else if (newHighlight == "creator") {
                    this.showAnnotationHightlight = false;
                    this.showCreatorHightlight = true;
                    this.showLicenseHightlight = false;
                    this.showReadmeHightlight = false;
                    setTimeout(() => {
                        this.showCreatorHightlight = false;
                    }, bestPracticeHighlightTime);
                } else if (newHighlight == "license") {
                    this.showAnnotationHightlight = false;
                    this.showCreatorHightlight = false;
                    this.showLicenseHightlight = true;
                    this.showReadmeHightlight = false;
                    setTimeout(() => {
                        this.showLicenseHightlight = false;
                    }, bestPracticeHighlightTime);
                } else if (newHighlight == "readme") {
                    this.showAnnotationHighlight = false;
                    this.showCreatorHightlight = false;
                    this.showLicenseHightlight = false;
                    this.showReadmeHightlight = true;
                    setTimeout(() => {
                        this.showReadmeHightlight = false;
                    }, bestPracticeHighlightTime);
                }
            },
        },
    },
    created() {
        this.services = new Services();
    },
    methods: {
        onTags(tags) {
            this.onAttributes({ tags });
            this.$emit("tags", tags);
        },
        onVersion() {
            this.$emit("version", this.versionCurrent);
        },
        onLicense(license) {
            this.$emit("license", license);
        },
        onCreator(creator) {
            this.$emit("creator", creator);
        },
        onError(error) {
            this.message = error;
            this.messageVariant = "danger";
        },
        onAttributes(data) {
            if (!this.id.includes("workflow-editor")) {
                this.services.updateWorkflow(this.id, data).catch((error) => {
                    this.onError(error);
                });
            }
        },
    },
};
</script>

<style>
.highlight-attribute {
    border: 1px outset;
    padding: 10px;
}

.best-practice-popover {
    max-width: 250px !important;
}
</style>
