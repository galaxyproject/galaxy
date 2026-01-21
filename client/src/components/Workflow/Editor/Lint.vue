<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { Steps } from "@/stores/workflowStepStore";

import type { LintState } from "./modules/linting";
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
} from "./modules/linting";
import type { useLintData } from "./modules/useLinting";

import GLink from "@/components/BaseComponents/GLink.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import LintSection from "@/components/Workflow/Editor/LintSection.vue";

const props = defineProps<{
    lintData: ReturnType<typeof useLintData>;
    steps: Steps; // Adjust the type as needed
    annotation?: String | null;
    readme?: String | null;
    license?: String | null;
    creator?: any;
    datatypesMapper: DatatypesMapperModel;
}>();

const { confirm } = useConfirmDialog();

const stores = useWorkflowStores();
const { stepStore, stateStore } = stores;
const { hasActiveOutputs } = storeToRefs(stepStore);

const { untypedParameters, unlabeledOutputs, untypedParameterWarnings, disconnectedInputs, missingMetadata } =
    props.lintData;

const showRefactor = computed(
    () => !untypedParameterWarnings.value.length || !disconnectedInputs.value.length || !unlabeledOutputs.value.length,
);

const checkAnnotation = computed(() => Boolean(props.annotation));
const checkAnnotationLength = computed(() => Boolean(!props.annotation || props.annotation.length <= 250));
const annotationLengthSuccessMessage = computed(() =>
    props.annotation
        ? "This workflow has a short description of appropriate length."
        : "This workflow does not have a short description.",
);
const checkReadme = computed(() => Boolean(props.readme));
const checkLicense = computed(() => Boolean(props.license));
const checkCreator = computed(() => (props.creator ? props.creator.length > 0 : false));

const emit = defineEmits<{
    (e: "onAttributes", highlight: { highlight: "highlight" }): void;
    (
        e: "onRefactor",
        action:
            | [
                  | ReturnType<typeof fixUntypedParameter>
                  | ReturnType<typeof fixDisconnectedInput>
                  | ReturnType<typeof fixUnlabeledOutputs>,
              ]
            | ReturnType<typeof fixAllIssues>,
    ): void;
    (e: "onScrollTo", stepId: Number): void;
    (e: "onHighlight", stepId: Number): void;
    (e: "onUnhighlight", stepId: Number): void;
}>();

function onAttributes(highlight: string) {
    emit("onAttributes", { highlight: "highlight" });
}

async function onFixUntypedParameter(item: LintState) {
    const confirmed = await confirm(
        "This issue can be fixed automatically by creating an explicit parameter input step. Do you want to proceed?",
        "Fix Untyped Parameter",
    );

    if (confirmed) {
        emit("onRefactor", [fixUntypedParameter(item)]);
    } else {
        emit("onScrollTo", item.stepId);
    }
}

async function onFixDisconnectedInput(item: LintState) {
    const confirmed = await confirm(
        "This issue can be fixed automatically by creating an explicit data input step. Do you want to proceed?",
        "Fix Disconnected Input",
    );
    if (confirmed) {
        emit("onRefactor", [fixDisconnectedInput(item)]);
    } else {
        emit("onScrollTo", item.stepId);
    }
}

async function onFixUnlabeledOutputs(item: LintState) {
    const confirmed = await confirm(
        "This issue can be fixed automatically by removing all unlabeled workflow outputs. Do you want to proceed?",
        "Fix Unlabeled Outputs",
    );
    if (confirmed) {
        emit("onRefactor", [fixUnlabeledOutputs()]);
    } else {
        emit("onScrollTo", item.stepId);
    }
}

function openAndFocus(item: LintState) {
    stateStore.activeNodeId = item.stepId;
    emit("onScrollTo", item.stepId);
}

function onHighlight(item: LintState) {
    emit("onHighlight", item.stepId);
}

function onUnhighlight(item: LintState) {
    emit("onUnhighlight", item.stepId);
}

function onRefactor() {
    if (untypedParameters.value) {
        const actions = fixAllIssues(props.steps, untypedParameters.value, props.datatypesMapper, stores);
        emit("onRefactor", actions);
    }
}
</script>
<template>
    <ActivityPanel title="Best Practices Review">
        <template v-if="showRefactor" v-slot:header>
            <GLink class="refactor-button" @click="onRefactor"> Try to automatically fix issues. </GLink>
        </template>
        <LintSection
            data-description="linting has annotation"
            :okay="checkAnnotation"
            success-message="This workflow has a short description. Ideally, this helps the executors of the workflow
                    understand the purpose and usage of the workflow."
            :warning-message="bestPracticeWarningAnnotation"
            attribute-link="Describe your Workflow."
            @onClickAttribute="onAttributes('annotation')" />
        <LintSection
            :okay="checkAnnotationLength"
            :success-message="annotationLengthSuccessMessage"
            :warning-message="bestPracticeWarningAnnotationLength"
            attribute-link="Shorten your Workflow Description."
            @onClickAttribute="onAttributes('annotation')" />
        <LintSection
            :okay="checkReadme"
            success-message="This workflow has a readme. Ideally, this helps the researchers understand the purpose, limitations, and usage of the workflow."
            :warning-message="bestPracticeWarningReadme"
            attribute-link="Provide Readme for your Workflow."
            @onClickAttribute="onAttributes('readme')" />
        <LintSection
            data-description="linting has creator"
            :okay="checkCreator"
            success-message="This workflow defines creator information."
            :warning-message="bestPracticeWarningCreator"
            attribute-link="Provide Creator Details."
            @onClickAttribute="onAttributes('creator')" />
        <LintSection
            data-description="linting has license"
            :okay="checkLicense"
            success-message="This workflow defines a license."
            :warning-message="bestPracticeWarningLicense"
            attribute-link="Specify a License."
            @onClickAttribute="onAttributes('license')" />
        <LintSection
            data-description="linting formal inputs"
            success-message="Workflow parameters are using formal input parameters."
            warning-message="This workflow uses legacy workflow parameters. They should be replaced with
                formal workflow inputs. Formal input parameters make tracking workflow provenance, usage within subworkflows,
                and executing the workflow via the API more robust:"
            :warning-items="untypedParameterWarnings"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="onFixUntypedParameter" />
        <LintSection
            data-description="linting connected"
            success-message="All non-optional inputs to workflow steps are connected to formal input parameters."
            warning-message="Some non-optional inputs are not connected to formal workflow inputs. Formal input parameters
                make tracking workflow provenance, usage within subworkflows, and executing the workflow via the API more robust:"
            :warning-items="disconnectedInputs"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="onFixDisconnectedInput" />
        <LintSection
            data-description="linting input metadata"
            success-message="All workflow inputs have labels and annotations."
            warning-message="Some workflow inputs are missing labels and/or annotations:"
            :warning-items="missingMetadata"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="openAndFocus" />
        <LintSection
            data-description="linting output labels"
            success-message="This workflow has outputs and they all have valid labels."
            warning-message="The following workflow outputs have no labels, they should be assigned a useful label or
                    unchecked in the workflow editor to mark them as no longer being a workflow output:"
            :warning-items="unlabeledOutputs"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="onFixUnlabeledOutputs" />
        <div v-if="!hasActiveOutputs">
            <FontAwesomeIcon :icon="faExclamationTriangle" class="text-warning" />
            <span>This workflow has no labeled outputs, please select and label at least one output.</span>
        </div>
    </ActivityPanel>
</template>
