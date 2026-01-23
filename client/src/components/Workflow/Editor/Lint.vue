<script setup lang="ts">
import { faCheck, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { type ConfirmDialogOptions, useConfirmDialog } from "@/composables/confirmDialog";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { Steps } from "@/stores/workflowStepStore";

import type { Rectangle } from "./modules/geometry";
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
import GCard from "@/components/Common/GCard.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import LintSection from "@/components/Workflow/Editor/LintSection.vue";

const props = defineProps<{
    lintData: ReturnType<typeof useLintData>;
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
    resolvedIssues,
    totalIssues,
    unlabeledOutputs,
    untypedParameterWarnings,
    disconnectedInputs,
    duplicateLabels,
    missingMetadata,
} = props.lintData;

const showRefactor = computed(
    () => untypedParameterWarnings.value.length || disconnectedInputs.value.length || unlabeledOutputs.value.length,
);

const annotationLengthSuccessMessage = computed(() =>
    checkAnnotation.value
        ? "This workflow has a short description of appropriate length."
        : "This workflow does not have a short description.",
);

/** Checks if the step indices in the workflow are consistent (i.e., sequential starting from 0). */
const stepIndicesConsistent = computed(() => {
    const stepIds = Object.keys(props.steps)
        .map((id) => parseInt(id, 10))
        .sort((a, b) => a - b);
    for (let i = 0; i < stepIds.length; i++) {
        if (stepIds[i] !== i) {
            return false;
        }
    }
    return true;
});

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
        emit("onRefactor", [fixUntypedParameter(item)]);
    } else {
        emit("onScrollTo", item.stepId);
    }
}

async function onFixDisconnectedInput(item: LintState) {
    // Since users can move around/delete steps, the step indices can be inconsistent (e.g.: 0,3,4 vs 0,1,2).
    // Therefore, for disconnected inputs, we first ask the user to save changes, which updates the step indices
    // to be consistent in the parent (`Index.vue`), and then the user can try fixing the issue again.

    // Note that this assumes that the parent component (`Index.vue`) updates step indices on save.
    // And then we have an additional check to see if the step indices are consistent.
    if (props.hasChanges || !stepIndicesConsistent.value) {
        await saveChanges(false);
        return;
    }

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
    const bounds = searchStore.getBoundsForItemCached(item.stepId, item.highlightType || "step", item.name);
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
        <template v-if="showRefactor" v-slot:header>
            <GLink class="refactor-button" @click="onRefactor"> Try to automatically fix issues. </GLink>
        </template>
        <template v-slot:header-buttons>
            <div class="text-nowrap">
                <FontAwesomeIcon
                    v-if="resolvedIssues === totalIssues"
                    :icon="faCheck"
                    class="text-success"
                    title="All best practices issues resolved!" />
                <FontAwesomeIcon
                    v-else
                    :icon="faExclamationTriangle"
                    class="text-warning"
                    :title="`${resolvedIssues} out of ${totalIssues} best practice issues resolved`" />
                {{ resolvedIssues }} / {{ totalIssues }}
            </div>
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
            v-if="checkAnnotation"
            data-description="linting annotation length"
            :okay="checkAnnotationLength"
            :success-message="annotationLengthSuccessMessage"
            :warning-message="bestPracticeWarningAnnotationLength"
            attribute-link="Shorten your Workflow Description."
            @onClickAttribute="onAttributes('annotation')" />
        <LintSection
            data-description="linting has readme"
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
            v-if="Object.keys(props.steps).length"
            data-description="linting formal inputs"
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
            success-message="All non-optional inputs to workflow steps are connected to formal input parameters."
            warning-message="Some non-optional inputs are not connected to formal workflow inputs. Formal input parameters
                make tracking workflow provenance, usage within subworkflows, and executing the workflow via the API more robust:"
            :warning-items="disconnectedInputs"
            @onMouseOver="onHighlight"
            @onClick="onFixDisconnectedInput" />
        <LintSection
            v-if="hasInputSteps"
            data-description="linting input metadata"
            success-message="All workflow inputs have labels and annotations."
            warning-message="Some workflow inputs are missing labels and/or annotations:"
            :warning-items="missingMetadata"
            @onMouseOver="onHighlight"
            @onClick="openAndFocus" />
        <template v-if="hasActiveOutputs">
            <LintSection
                data-description="linting duplicate output labels"
                success-message="All workflow output labels are unique."
                warning-message="Some workflow outputs have duplicate labels. Workflow output labels must be unique:"
                :warning-items="duplicateLabels"
                @onMouseOver="onHighlight"
                @onClick="openAndFocus" />
            <LintSection
                data-description="linting unlabeled outputs"
                success-message="All workflow outputs have valid (populated) labels."
                warning-message="The following workflow outputs have no labels, they should be assigned a useful label or
                    unchecked in the workflow editor to mark them as no longer being a workflow output:"
                :warning-items="unlabeledOutputs"
                @onMouseOver="onHighlight"
                @onClick="onFixUnlabeledOutputs" />
        </template>
        <GCard v-else data-description="linting no outputs">
            <div>
                <FontAwesomeIcon :icon="faExclamationTriangle" class="text-warning" />
                <span>This workflow has no labeled outputs, please select and label at least one output.</span>
            </div>
        </GCard>
    </ActivityPanel>
</template>
