<template>
    <ActivityPanel id="edit-attributes" title="属性" itemscope itemtype="http://schema.org/CreativeWork">
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <div id="workflow-name-area">
            <b>名称</b>
            <meta itemprop="name" :content="name" />
            <b-input
                id="workflow-name"
                v-model="nameCurrent"
                :state="!nameCurrent ? false : null"
                @keyup="$emit('update:nameCurrent', nameCurrent)" />
        </div>
        <div v-if="versionOptions.length > 0" id="workflow-version-area" class="mt-2">
            <b>版本</b>
            <b-form-select v-model="versionCurrent" @change="onVersion">
                <b-form-select-option v-for="v in versionOptions" :key="v.version" :value="v.version">
                    {{ v.label }}
                </b-form-select-option>
            </b-form-select>
        </div>
        <div v-if="hasParameters" id="workflow-parameters-area" class="mt-2">
            <b>参数</b>
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
            <b>简短描述</b>
            <meta itemprop="description" :content="annotationCurrent" />
            <b-textarea
                id="workflow-annotation"
                v-model="annotationCurrent"
                @keyup="$emit('update:annotationCurrent', annotationCurrent)" />
            <div class="form-text text-muted">
                当查看此工作流时，将显示此简短描述，建议限制在一两句话内。
            </div>
            <b-popover
                custom-class="best-practice-popover"
                target="workflow-annotation"
                boundary="window"
                placement="right"
                :show.sync="showAnnotationHightlight"
                triggers="manual"
                title="最佳实践"
                :content="annotationBestPracticeMessage">
            </b-popover>
        </div>
        <div
            id="workflow-license-area"
            class="mt-2"
            :class="{ 'bg-secondary': showLicenseHightlight, 'highlight-attribute': showLicenseHightlight }">
            <b>许可证</b>
            <LicenseSelector id="license-selector" :input-license="license" @onLicense="onLicense" />
            <b-popover
                custom-class="best-practice-popover"
                target="license-selector"
                boundary="window"
                placement="right"
                :show.sync="showLicenseHightlight"
                triggers="manual"
                title="最佳实践"
                :content="bestPracticeWarningLicense">
            </b-popover>
        </div>
        <div
            id="workflow-creator-area"
            class="mt-2"
            :class="{ 'bg-secondary': showCreatorHightlight, 'highlight-attribute': showCreatorHightlight }">
            <b>创建者</b>
            <CreatorEditor id="creator-editor" :creators="creatorAsList" @onCreators="onCreator" />
            <b-popover
                custom-class="best-practice-popover"
                target="creator-editor"
                boundary="window"
                placement="right"
                :show.sync="showCreatorHightlight"
                triggers="manual"
                title="最佳实践"
                :content="bestPracticeWarningCreator">
            </b-popover>
        </div>
        <div class="mt-2">
            <b>标签</b>
            <StatelessTags :value="tags" @input="onTags" />
            <div class="form-text text-muted">
                应用标签以便于搜索和查找具有相同标签的项目。
            </div>
        </div>
        <div class="mt-2">
            <b
                >自述文件
                <FontAwesomeIcon :icon="faEye" @click="showReadmePreview = true" />
            </b>
            <b-textarea
                id="workflow-readme"
                v-model="readmeCurrent"
                @keyup="$emit('update:readmeCurrent', readmeCurrent)" />
            <div class="form-text text-muted">
                详细描述工作流的功能。最好包括所需数据类型的描述。研究人员在寻找工作流时会看到此文本。支持 Markdown。
            </div>
        </div>
        <div class="mt-2">
            <b>帮助</b>
            <b-textarea id="workflow-help" v-model="helpCurrent" @keyup="$emit('update:helpCurrent', helpCurrent)" />
            <div class="form-text text-muted">
                详细描述如何使用工作流及其调试方法。研究人员在运行此工作流时会看到此文本。支持 Markdown。
            </div>
        </div>
        <div class="mt-2">
            <b>Logo URL</b>
            <b-input
                id="workflow-logo-url"
                v-model="logoUrlCurrent"
                @keyup="$emit('update:logoUrlCurrent', logoUrlCurrent)" />
            <div class="form-text text-muted">
                在生成工作流的发布物时使用的 logo 图片。这是完全可选的。
            </div>
        </div>
        <BModal v-model="showReadmePreview" hide-header centered ok-only>
            <ToolHelpMarkdown :content="readmePreviewMarkdown" />
        </BModal>
    </ActivityPanel>
</template>

<script>
import { faEye } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BModal } from "bootstrap-vue";
import { format, parseISO } from "date-fns";

import { Services } from "@/components/Workflow/services";

import {
    bestPracticeWarningAnnotation,
    bestPracticeWarningAnnotationLength,
    bestPracticeWarningCreator,
    bestPracticeWarningLicense,
} from "./modules/linting";
import { UntypedParameters } from "./modules/parameters";

import LicenseSelector from "@/components/License/LicenseSelector.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import CreatorEditor from "@/components/SchemaOrg/CreatorEditor.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import ToolHelpMarkdown from "@/components/Tool/ToolHelpMarkdown.vue";

const bestPracticeHighlightTime = 10000;

export default {
    name: "工作流属性",
    components: {
        FontAwesomeIcon,
        StatelessTags,
        LicenseSelector,
        CreatorEditor,
        ActivityPanel,
        BModal,
        ToolHelpMarkdown,
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
            showReadmePreview: false,
            faEye,
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
        readmePreviewMarkdown() {
            let content = "";
            if (this.nameCurrent) {
                content += `# ${this.nameCurrent}\n\n`;
            }
            if (this.logoUrlCurrent) {
                content += `![${this.nameCurrent || "workflow"} logo](${this.logoUrlCurrent})\n\n`;
            }
            if (this.readmeCurrent) {
                content += this.readmeCurrent;
            }
            return content;
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
        annotationBestPracticeMessage() {
            if (this.annotationCurrent) {
                return bestPracticeWarningAnnotationLength;
            } else {
                return bestPracticeWarningAnnotation;
            }
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
            this.showAnnotationHightlight = false;
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
