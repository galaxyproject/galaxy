<template>
    <ActivityPanel title="最佳实践审核">
        <template v-if="showRefactor" v-slot:header>
            <button class="refactor-button ui-link" @click="onRefactor">尝试自动修复问题。</button>
        </template>
        <LintSection
            :okay="checkAnnotation"
            success-message="此工作流有简短的描述。理想情况下，这有助于工作流的执行者理解工作流的目的和使用方法。"
            :warning-message="bestPracticeWarningAnnotation"
            attribute-link="描述您的工作流。"
            @onClick="onAttributes('annotation')" />
        <LintSection
            :okay="checkAnnotationLength"
            :success-message="annotationLengthSuccessMessage"
            :warning-message="bestPracticeWarningAnnotationLength"
            attribute-link="缩短您的工作流描述。"
            @onClick="onAttributes('annotation')" />
        <LintSection
            :okay="checkReadme"
            success-message="此工作流有一个自述文件。理想情况下，这有助于研究人员理解工作流的目的、限制和使用方法。"
            :warning-message="bestPracticeWarningReadme"
            attribute-link="为您的工作流提供自述文件。"
            @onClick="onAttributes('readme')" />
        <LintSection
            :okay="checkCreator"
            success-message="此工作流定义了创建者信息。"
            :warning-message="bestPracticeWarningCreator"
            attribute-link="提供创建者详细信息。"
            @onClick="onAttributes('creator')" />
        <LintSection
            :okay="checkLicense"
            success-message="此工作流定义了许可证。"
            :warning-message="bestPracticeWarningLicense"
            attribute-link="指定许可证。"
            @onClick="onAttributes('license')" />
        <LintSection
            success-message="工作流参数使用正式输入参数。"
            warning-message="此工作流使用了旧版工作流参数，应替换为正式工作流输入。正式输入参数使得跟踪工作流的来源、在子工作流中的使用以及通过 API 执行工作流更为健壮："
            :warning-items="warningUntypedParameters"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="onFixUntypedParameter" />
        <LintSection
            success-message="所有工作流步骤的非可选输入都已连接到正式输入参数。"
            warning-message="一些非可选输入未连接到正式工作流输入。正式输入参数使得跟踪工作流的来源、在子工作流中的使用以及通过 API 执行工作流更为健壮："
            :warning-items="warningDisconnectedInputs"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="onFixDisconnectedInput" />
        <LintSection
            success-message="所有工作流输入都有标签和注释。"
            warning-message="一些工作流输入缺少标签和/或注释："
            :warning-items="warningMissingMetadata"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="openAndFocus" />
        <LintSection
            success-message="此工作流有输出，且所有输出都有有效的标签。"
            warning-message="以下工作流输出没有标签，应为其分配有用的标签，或在工作流编辑器中取消勾选，标记它们不再是工作流输出："
            :warning-items="warningUnlabeledOutputs"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="onFixUnlabeledOutputs" />
        <div v-if="!hasActiveOutputs">
            <FontAwesomeIcon icon="exclamation-triangle" class="text-warning" />
            <span>此工作流没有标记的输出，请选择并标记至少一个输出。</span>
        </div>
    </ActivityPanel>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExclamationTriangle, faMagic } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import { UntypedParameters } from "components/Workflow/Editor/modules/parameters";
import { storeToRefs } from "pinia";
import Vue from "vue";

import { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStores } from "@/composables/workflowStores";

import {
    bestPracticeWarningAnnotation,
    bestPracticeWarningAnnotationLength,
    bestPracticeWarningCreator,
    bestPracticeWarningLicense,
    bestPracticeWarningReadme,
    fixAllIssues,
    fixDisconnectedInput,
    fixUnlabeledOutputs,
    fixUntypedParameter,
    getDisconnectedInputs,
    getMissingMetadata,
    getUnlabeledOutputs,
    getUntypedParameters,
} from "./modules/linting";

import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import LintSection from "@/components/Workflow/Editor/LintSection.vue";

Vue.use(BootstrapVue);

library.add(faExclamationTriangle);
library.add(faMagic);

export default {
    components: {
        FontAwesomeIcon,
        LintSection,
        ActivityPanel,
    },
    props: {
        untypedParameters: {
            type: UntypedParameters,
            required: true,
        },
        steps: {
            type: Object,
            required: true,
        },
        annotation: {
            type: String,
            default: null,
        },
        license: {
            type: String,
            default: null,
        },
        creator: {
            type: Array,
            default: null,
        },
        datatypesMapper: {
            type: DatatypesMapperModel,
            required: true,
        },
    },
    setup() {
        const stores = useWorkflowStores();
        const { connectionStore, stepStore, stateStore } = stores;
        const { hasActiveOutputs } = storeToRefs(stepStore);
        return { stores, connectionStore, stepStore, hasActiveOutputs, stateStore };
    },
    data() {
        return {
            bestPracticeWarningAnnotation: bestPracticeWarningAnnotation,
            bestPracticeWarningAnnotationLength: bestPracticeWarningAnnotationLength,
            bestPracticeWarningCreator: bestPracticeWarningCreator,
            bestPracticeWarningLicense: bestPracticeWarningLicense,
            bestPracticeWarningReadme: bestPracticeWarningReadme,
        };
    },
    computed: {
        showRefactor() {
            // we could be even more precise here and check the inputs and such, because
            // some of these extractions may not be possible.
            return !this.checkUntypedParameters || !this.checkDisconnectedInputs || !this.checkUnlabeledOutputs;
        },
        checkAnnotation() {
            return !!this.annotation;
        },
        checkAnnotationLength() {
            const annotation = this.annotation;
            if (annotation && annotation.length > 250) {
                return false;
            }
            return true;
        },
        annotationLengthSuccessMessage() {
            if (this.annotation) {
                return "此工作流有一个适当长度的简短描述。";
            } else {
                return "此工作流没有简短描述。";
            }
        },
        checkReadme() {
            return !!this.annotation;
        },
        checkLicense() {
            return !!this.license;
        },
        checkCreator() {
            if (this.creator instanceof Array) {
                return this.creator.length > 0;
            } else {
                return !!this.creator;
            }
        },
        checkUntypedParameters() {
            return this.warningUntypedParameters.length == 0;
        },
        checkDisconnectedInputs() {
            return this.warningDisconnectedInputs.length == 0;
        },
        checkUnlabeledOutputs() {
            return this.warningUnlabeledOutputs.length == 0;
        },
        warningUntypedParameters() {
            return getUntypedParameters(this.untypedParameters);
        },
        warningDisconnectedInputs() {
            return getDisconnectedInputs(this.steps, this.datatypesMapper, this.stores);
        },
        warningMissingMetadata() {
            return getMissingMetadata(this.steps);
        },
        warningUnlabeledOutputs() {
            return getUnlabeledOutputs(this.steps);
        },
    },
    methods: {
        onAttributes(highlight) {
            const args = { highlight: highlight };
            this.$emit("onAttributes", args);
        },
        onFixUntypedParameter(item) {
            if (
                confirm(
                    "此问题可以通过创建一个明确的参数输入步骤自动修复。您想继续吗？"
                )
            ) {
                this.$emit("onRefactor", [fixUntypedParameter(item)]);
            } else {
                this.$emit("onScrollTo", item.stepId);
            }
        },
        onFixDisconnectedInput(item) {
            if (
                confirm(
                    "此问题可以通过创建一个明确的数据输入步骤自动修复。您想继续吗？"
                )
            ) {
                this.$emit("onRefactor", [fixDisconnectedInput(item)]);
            } else {
                this.$emit("onScrollTo", item.stepId);
            }
        },
        onFixUnlabeledOutputs(item) {
            if (
                confirm(
                    "此问题可以通过移除所有未标记的工作流输出自动修复。您想继续吗？"
                )
            ) {
                this.$emit("onRefactor", [fixUnlabeledOutputs()]);
            } else {
                this.$emit("onScrollTo", item.stepId);
            }
        },
        openAndFocus(item) {
            this.stateStore.activeNodeId = item.stepId;
            this.$emit("onScrollTo", item.stepId);
        },
        onHighlight(item) {
            this.$emit("onHighlight", item.stepId);
        },
        onUnhighlight(item) {
            this.$emit("onUnhighlight", item.stepId);
        },
        onRefactor() {
            const actions = fixAllIssues(this.steps, this.untypedParameters, this.datatypesMapper, this.stores);
            this.$emit("onRefactor", actions);
        },
    },
};
</script>
