import { storeToRefs } from "pinia";
import type { Ref } from "vue";
import { computed, ref, watch } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { Steps } from "@/stores/workflowStepStore";

import type { LintState } from "./linting";
import {
    getDisconnectedInputs,
    getDuplicateLabels,
    getMissingMetadata,
    getUnlabeledOutputs,
    getUntypedParameters,
} from "./linting";
import { getUntypedWorkflowParameters, type UntypedParameters } from "./parameters";

export interface LintData {
    resolvedIssues: Ref<number>;
    totalIssues: Ref<number>;
    untypedParameters: Ref<LintState[]>;
    untypedParameterWarnings: Ref<LintState[]>;
    disconnectedInputs: Ref<LintState[]>;
    duplicateLabels: Ref<LintState[]>;
    unlabeledOutputs: Ref<LintState[]>;
    missingMetadata: Ref<LintState[]>;
}

export function useLintData(
    workflowId: Ref<string>,
    steps: Ref<Steps>,
    datatypesMapper: Ref<DatatypesMapperModel>,
    annotation?: Ref<string | null>,
    readme?: Ref<string | null>,
    license?: Ref<string | null>,
    creator?: Ref<any>, // TODO: Define creator type
) {
    const workflowStores = useWorkflowStores(workflowId);

    const untypedParameters = ref<UntypedParameters>();
    const untypedParameterWarnings = ref<LintState[]>([]);
    const disconnectedInputs = ref<LintState[]>([]);
    const duplicateLabels = ref<LintState[]>([]);
    const unlabeledOutputs = ref<LintState[]>([]);
    const missingMetadata = ref<LintState[]>([]);

    watch(
        () => [steps, datatypesMapper.value],
        () => {
            if (datatypesMapper.value) {
                untypedParameters.value = getUntypedWorkflowParameters(steps.value);
                untypedParameterWarnings.value = getUntypedParameters(untypedParameters.value);
                disconnectedInputs.value = getDisconnectedInputs(steps.value, datatypesMapper.value, workflowStores);
                duplicateLabels.value = getDuplicateLabels(steps.value, workflowStores);
                unlabeledOutputs.value = getUnlabeledOutputs(steps.value);
                missingMetadata.value = getMissingMetadata(steps.value);
            }
        },
        { immediate: true, deep: true },
    );

    const checkAnnotation = computed(() => Boolean(annotation?.value));
    const checkAnnotationLength = computed(() => Boolean(annotation?.value && annotation.value.length <= 250));
    const checkReadme = computed(() => Boolean(readme?.value));
    const checkLicense = computed(() => Boolean(license?.value));
    const checkCreator = computed(() => (creator?.value ? creator.value.length > 0 : false));

    const { stepStore } = workflowStores;
    const { hasActiveOutputs, hasInputSteps } = storeToRefs(stepStore);

    /** This computes the `LintSection`s, some of which are conditionally rendered
     * in `Lint.vue`. This is used to compute the total and resolved best practice issues.
     *
     * TODO: Maybe this could be used to decide which section is rendered in the parent component as well?
     */
    const lintingSections = computed(() => [
        {
            name: "annotation",
            exists: true,
            resolved: checkAnnotation.value,
        },
        {
            name: "annotationLength",
            exists: checkAnnotation.value,
            resolved: checkAnnotationLength.value,
        },
        {
            name: "readme",
            exists: true,
            resolved: checkReadme.value,
        },
        {
            name: "creator",
            exists: true,
            resolved: checkCreator.value,
        },
        {
            name: "license",
            exists: true,
            resolved: checkLicense.value,
        },
        {
            name: "untypedParameters",
            exists: Object.keys(steps.value).length > 0,
            resolved: untypedParameterWarnings.value.length === 0,
        },
        {
            name: "disconnectedInputs",
            exists: Object.keys(steps.value).length > 0,
            resolved: disconnectedInputs.value.length === 0,
        },
        {
            name: "missingMetadata",
            exists: hasInputSteps.value,
            resolved: missingMetadata.value.length === 0,
        },
        {
            name: "duplicateLabels",
            exists: hasActiveOutputs.value,
            resolved: duplicateLabels.value.length === 0,
        },
        {
            name: "unlabeledOutputs",
            exists: hasActiveOutputs.value,
            resolved: unlabeledOutputs.value.length === 0,
        },
        {
            name: "noOutputs",
            exists: !hasActiveOutputs.value,
            resolved: false,
        },
    ]);

    const totalIssues = computed(() => lintingSections.value.filter((section) => section.exists).length);

    const resolvedIssues = computed(
        () => lintingSections.value.filter((section) => section.exists && section.resolved).length,
    );

    return {
        checkAnnotation,
        checkAnnotationLength,
        checkReadme,
        checkLicense,
        checkCreator,
        resolvedIssues,
        totalIssues,
        untypedParameters,
        untypedParameterWarnings,
        disconnectedInputs,
        duplicateLabels,
        unlabeledOutputs,
        missingMetadata,
    };
}
