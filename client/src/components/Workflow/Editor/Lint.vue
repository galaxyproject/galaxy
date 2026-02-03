<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, toRefs } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { type ConfirmDialogOptions, useConfirmDialog } from "@/composables/confirmDialog";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { Steps } from "@/stores/workflowStepStore";

import type { Rectangle } from "./modules/geometry";
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
    isStateForInputOrOutput,
} from "./modules/linting";
import type { DisconnectedInputState, LintState, UntypedParameterState } from "./modules/lintingTypes";
import type { LintData } from "./modules/useLinting";

import LintSectionSeparator from "./LintSectionSeparator.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import LintSection from "@/components/Workflow/Editor/LintSection.vue";

const props = defineProps<{
    lintData: LintData;
    steps: Steps; // Adjust the type as needed
    datatypesMapper: DatatypesMapperModel;
    hasChanges: boolean;
    onSave?: () => Promise<boolean>;
}>();

const { confirm } = useConfirmDialog();

const stores = useWorkflowStores();
const { stepStore, stateStore, searchStore } = stores;
const { hasActiveOutputs, hasInputSteps } = storeToRefs(stepStore);

const {
    checkAnnotation,
    checkAnnotationLength,
    checkReadme,
    checkLicense,
    checkCreator,
    resolvedPriorityIssues,
    totalPriorityIssues,
    resolvedAttributeIssues,
    totalAttributeIssues,
    unlabeledOutputs,
    untypedParameterWarnings,
    disconnectedInputs,
    duplicateLabels,
    missingMetadata,
} = toRefs(props.lintData);

/** Renders the celebratory reaction when all critical and non-critical best practice issues are resolved. */
const showSuccessReaction = computed(
    () =>
        resolvedPriorityIssues.value === totalPriorityIssues.value &&
        totalPriorityIssues.value > 0 &&
        resolvedAttributeIssues.value === totalAttributeIssues.value &&
        totalAttributeIssues.value > 0,
);

const showRefactor = computed(
    () => untypedParameterWarnings.value.length || disconnectedInputs.value.length || unlabeledOutputs.value.length,
);

const emit = defineEmits<{
    (e: "onAttributes", highlight: { highlight: string }): void;
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
    (e: "onHighlightRegion", bounds: Rectangle): void;
}>();

function onAttributes(highlight: string) {
    emit("onAttributes", { highlight });
}

/** Prompts the user to save changes.
 * @param canProceed - If `true`, the user is informed that by confirming, they will save the workflow
 *                     and then proceed to apply automatic fixes.
 *                     If `false`, the user is informed that they need to save and try fixing the issue again.
 * @returns A promise that resolves to true if the user saved changes, false otherwise.
 */
async function saveChanges(canProceed = true) {
    const confirmationMessageHead = "You have unsaved changes in the workflow editor. Please save your changes ";

    const confirmationMessage = canProceed
        ? confirmationMessageHead +
          "and there will be an attempt to automatically fix the issues. Do you want to save your changes and apply fixes now?"
        : confirmationMessageHead + "to enable automatic fixing of this issue. Do you want to save your changes now?";
    const confirmationOptions: ConfirmDialogOptions = canProceed
        ? { title: "Unsaved Changes", okTitle: "Save Changes and Fix Issues" }
        : { title: "Save Workflow and Check Issues Again", okTitle: "Save Changes" };

    const proceed = await confirm(confirmationMessage, confirmationOptions);
    if (proceed && props.onSave) {
        await props.onSave();
        return true;
    }
    return false;
}

async function onFixUntypedParameter(item: LintState) {
    const confirmed = await confirm(
        "This issue can be fixed automatically by creating an explicit parameter input step. Do you want to proceed?",
        "Fix Untyped Parameter",
    );

    if (confirmed) {
        emit("onRefactor", [fixUntypedParameter(item as UntypedParameterState)]);
    } else {
        emit("onScrollTo", item.stepId);
    }
}

async function onFixDisconnectedInput(item: LintState) {
    // Since users can move around/delete steps, the step indices can be inconsistent (e.g.: 0,3,4 vs 0,1,2).
    // Therefore, for disconnected inputs, we first ask the user to save changes, which updates the step indices
    // to be consistent in the parent (`Index.vue`), and then the user can try fixing the issue again.

    // Note that this assumes that the parent component (`Index.vue`) updates step indices on save.
    if (props.hasChanges) {
        await saveChanges(false);
        return;
    }

    const confirmed = await confirm(
        "This issue can be fixed automatically by creating an explicit data input step. Do you want to proceed?",
        "Fix Disconnected Input",
    );
    if (confirmed) {
        emit("onRefactor", [fixDisconnectedInput(item as DisconnectedInputState)]);
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
    const bounds = searchStore.getBoundsForItemCached(
        item.stepId,
        isStateForInputOrOutput(item) ? item.highlightType : "step",
        "name" in item ? item.name : undefined,
    );
    if (bounds) {
        emit("onHighlightRegion", bounds);
    }
}

async function onRefactor() {
    if (showRefactor.value) {
        // If there are unsaved changes, the user can choose to save and proceed to automatically fix issues.
        if (props.hasChanges && !(await saveChanges())) {
            return;
        }

        const actions = fixAllIssues(untypedParameterWarnings.value, disconnectedInputs.value, unlabeledOutputs.value);
        emit("onRefactor", actions);
    }
}
</script>
<template>
    <ActivityPanel title="Best Practices Review">
        <template v-slot:header>
            <LintSectionSeparator
                section-type="critical"
                :resolved-issues="resolvedPriorityIssues"
                :total-issues="totalPriorityIssues" />
        </template>
        <div
            class="success-reaction"
            :class="{
                'success-reaction--show': showSuccessReaction,
            }">
            🎉
        </div>

        <GLink v-if="showRefactor" class="mb-2" data-description="auto fix lint issues" @click="onRefactor">
            Try to automatically fix issues.
        </GLink>

        <LintSection
            v-if="Object.keys(props.steps).length"
            data-description="linting formal inputs"
            high-priority
            success-message="Workflow parameters are using formal input parameters."
            warning-message="This workflow uses legacy workflow parameters. They should be replaced with
                formal workflow inputs. Formal input parameters make tracking workflow provenance, usage within subworkflows,
                and executing the workflow via the API more robust:"
            :warning-items="untypedParameterWarnings"
            @onMouseOver="onHighlight"
            @onClick="onFixUntypedParameter" />
        <LintSection
            v-if="Object.keys(props.steps).length"
            data-description="linting connected"
            high-priority
            success-message="All non-optional inputs to workflow steps are connected to formal input parameters."
            warning-message="Some non-optional inputs are not connected to formal workflow inputs. Formal input parameters
                make tracking workflow provenance, usage within subworkflows, and executing the workflow via the API more robust:"
            :warning-items="disconnectedInputs"
            :requires-save="props.hasChanges"
            @onMouseOver="onHighlight"
            @onClick="onFixDisconnectedInput"
            @onSaveRequested="saveChanges(false)" />
        <LintSection
            v-if="hasInputSteps"
            data-description="linting input metadata"
            high-priority
            success-message="All workflow inputs have labels and annotations."
            warning-message="Some workflow inputs are missing labels and/or annotations:"
            :warning-items="missingMetadata"
            @onMouseOver="onHighlight"
            @onClick="openAndFocus" />
        <template v-if="hasActiveOutputs">
            <LintSection
                data-description="linting duplicate output labels"
                high-priority
                success-message="All workflow output labels are unique."
                warning-message="Some workflow outputs have duplicate labels. Workflow output labels must be unique:"
                :warning-items="duplicateLabels"
                @onMouseOver="onHighlight"
                @onClick="openAndFocus" />
            <LintSection
                data-description="linting unlabeled outputs"
                high-priority
                success-message="All workflow outputs have valid (populated) labels."
                warning-message="The following workflow outputs have no labels, they should be assigned a useful label or
                    unchecked in the workflow editor to mark them as no longer being a workflow output:"
                :warning-items="unlabeledOutputs"
                @onMouseOver="onHighlight"
                @onClick="onFixUnlabeledOutputs" />
        </template>
        <LintSection
            v-else
            data-description="linting no outputs"
            high-priority
            :okay="false"
            success-message="This workflow has labeled outputs."
            warning-message="This workflow has no labeled outputs, please select and label at least one output." />

        <LintSectionSeparator
            section-type="attributes"
            :resolved-issues="resolvedAttributeIssues"
            :total-issues="totalAttributeIssues" />

        <LintSection
            data-description="linting has annotation"
            :okay="checkAnnotation"
            success-message="This workflow has a short description."
            :warning-message="bestPracticeWarningAnnotation"
            attribute-link="Describe your Workflow."
            @onClickAttribute="onAttributes('annotation')" />
        <LintSection
            v-if="checkAnnotation && !checkAnnotationLength"
            data-description="linting annotation length"
            :okay="false"
            success-message="This workflow has a short description of appropriate length."
            :warning-message="bestPracticeWarningAnnotationLength"
            attribute-link="Shorten your Workflow Description."
            @onClickAttribute="onAttributes('annotation')" />
        <LintSection
            data-description="linting has readme"
            :okay="checkReadme"
            success-message="This workflow has a readme."
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
    </ActivityPanel>
</template>

<style scoped lang="scss">
.success-reaction {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(255, 255, 255, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 4rem;
    opacity: 0;
    visibility: hidden;
    transition:
        opacity 0.3s ease-in-out,
        visibility 0.3s ease-in-out;
    z-index: 1000;
    border-radius: 0.5rem;
    backdrop-filter: blur(4px);
}

.success-reaction--show {
    opacity: 1;
    visibility: visible;
    animation: celebration 2s ease-in-out forwards;
}

@keyframes celebration {
    0% {
        opacity: 0;
        transform: scale(0.8);
    }
    20% {
        opacity: 1;
        transform: scale(1.1);
    }
    80% {
        opacity: 1;
        transform: scale(1);
    }
    100% {
        opacity: 0;
        transform: scale(0.9);
    }
}
</style>
