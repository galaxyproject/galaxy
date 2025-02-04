<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExclamationTriangle, faMagic } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import { storeToRefs } from "pinia";
import Vue, { computed } from "vue";

import { type DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { Steps } from "@/stores/workflowStepStore";

import type { LintState } from "./modules/linting";
import {
    bestPracticeWarningAnnotation,
    bestPracticeWarningCreator,
    bestPracticeWarningLicense,
    fixAllIssues,
    fixDisconnectedInput,
    fixUnlabeledOutputs,
    fixUntypedParameter,
} from "./modules/linting";
import { type useLintData } from "./modules/useLinting";

import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import LintSection from "@/components/Workflow/Editor/LintSection.vue";

Vue.use(BootstrapVue);

library.add(faExclamationTriangle);
library.add(faMagic);

const props = defineProps<{
    lintData: ReturnType<typeof useLintData>;
    steps: Steps; // Adjust the type as needed
    annotation?: String | null;
    license?: String | null;
    creator?: any;
    datatypesMapper: DatatypesMapperModel;
}>();
const stores = useWorkflowStores();
const { stepStore, stateStore } = stores;
const { hasActiveOutputs } = storeToRefs(stepStore);
const { untypedParameters, unlabeledOutputs, untypedParameterWarnings, disconnectedInputs, missingMetadata } =
    props.lintData;
const showRefactor = computed(
    () => !untypedParameterWarnings.value.length || !disconnectedInputs.value.length || !unlabeledOutputs.value.length
);
const checkAnnotation = computed(() => !!props.annotation);
const checkLicense = computed(() => !!props.license);
const checkCreator = computed(() => (props.creator ? props.creator.length > 0 : false));

const emit = defineEmits<{
    (e: "onAttributes", highlight: { highlight: "highlight" }): void;
    (
        e: "onRefactor",
        action:
            | [
                  | ReturnType<typeof fixUntypedParameter>
                  | ReturnType<typeof fixDisconnectedInput>
                  | ReturnType<typeof fixUnlabeledOutputs>
              ]
            | ReturnType<typeof fixAllIssues>
    ): void;
    (e: "onScrollTo", stepId: Number): void;
    (e: "onHighlight", stepId: Number): void;
    (e: "onUnhighlight", stepId: Number): void;
}>();

function onAttributes(highlight: string) {
    emit("onAttributes", { highlight: "highlight" });
}
function onFixUntypedParameter(item: LintState) {
    if (
        confirm(
            "This issue can be fixed automatically by creating an explicit parameter input step. Do you want to proceed?"
        )
    ) {
        emit("onRefactor", [fixUntypedParameter(item)]);
    } else {
        emit("onScrollTo", item.stepId);
    }
}
function onFixDisconnectedInput(item: LintState) {
    if (
        confirm(
            "This issue can be fixed automatically by creating an explicit data input step. Do you want to proceed?"
        )
    ) {
        emit("onRefactor", [fixDisconnectedInput(item)]);
    } else {
        emit("onScrollTo", item.stepId);
    }
}

function onFixUnlabeledOutputs(item: LintState) {
    if (
        confirm(
            "This issue can be fixed automatically by removing all unlabeled workflow output. Do you want to proceed?"
        )
    ) {
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
            <button class="refactor-button ui-link" @click="onRefactor">Try to automatically fix issues.</button>
        </template>
        <LintSection
            :okay="checkAnnotation"
            success-message="This workflow is annotated. Ideally, this helps the executors of the workflow
                    understand the purpose and usage of the workflow."
            :warning-message="bestPracticeWarningAnnotation"
            attribute-link="Annotate your Workflow."
            @onClick="onAttributes('annotation')" />
        <LintSection
            :okay="checkCreator"
            success-message="This workflow defines creator information."
            :warning-message="bestPracticeWarningCreator"
            attribute-link="Provide Creator Details."
            @onClick="onAttributes('creator')" />
        <LintSection
            :okay="checkLicense"
            success-message="This workflow defines a license."
            :warning-message="bestPracticeWarningLicense"
            attribute-link="Specify a License."
            @onClick="onAttributes('license')" />
        <LintSection
            success-message="Workflow parameters are using formal input parameters."
            warning-message="This workflow uses legacy workflow parameters. They should be replaced with
                formal workflow inputs. Formal input parameters make tracking workflow provenance, usage within subworkflows,
                and executing the workflow via the API more robust:"
            :warning-items="untypedParameterWarnings"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="onFixUntypedParameter" />
        <LintSection
            success-message="All non-optional inputs to workflow steps are connected to formal input parameters."
            warning-message="Some non-optional inputs are not connected to formal workflow inputs. Formal input parameters
                make tracking workflow provenance, usage within subworkflows, and executing the workflow via the API more robust:"
            :warning-items="disconnectedInputs"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="onFixDisconnectedInput" />
        <LintSection
            success-message="All workflow inputs have labels and annotations."
            warning-message="Some workflow inputs are missing labels and/or annotations:"
            :warning-items="missingMetadata"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="openAndFocus" />
        <LintSection
            success-message="This workflow has outputs and they all have valid labels."
            warning-message="The following workflow outputs have no labels, they should be assigned a useful label or
                    unchecked in the workflow editor to mark them as no longer being a workflow output:"
            :warning-items="unlabeledOutputs"
            @onMouseOver="onHighlight"
            @onMouseLeave="onUnhighlight"
            @onClick="onFixUnlabeledOutputs" />
        <div v-if="!hasActiveOutputs">
            <FontAwesomeIcon icon="exclamation-triangle" class="text-warning" />
            <span>This workflow has no labeled outputs, please select and label at least one output.</span>
        </div>
    </ActivityPanel>
</template>
