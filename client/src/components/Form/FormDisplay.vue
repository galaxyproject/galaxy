<template>
    <FormInputs
        :key="id"
        :inputs="formInputs"
        :loading="loading"
        :prefix="prefix"
        :sustain-repeats="sustainRepeats"
        :sustain-conditionals="sustainConditionals"
        :collapsed-enable-text="collapsedEnableText"
        :collapsed-enable-icon="collapsedEnableIcon"
        :collapsed-disable-text="collapsedDisableText"
        :collapsed-disable-icon="collapsedDisableIcon"
        :on-change="onChange"
        :on-change-form="onChangeForm"
        :workflow-building-mode="workflowBuildingMode"
        :workflow-run="workflowRun"
        :active-node-id="activeNodeId"
        :sync-with-graph="syncWithGraph"
        :steps-not-matching-request="stepsNotMatchingRequest"
        @stop-flagging="emit('stop-flagging')"
        @update:active-node-id="updateActiveNode" />
</template>

<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faCaretSquareDown, faCaretSquareUp } from "@fortawesome/free-regular-svg-icons";
import { getCurrentInstance, toRef, watch } from "vue";

import type { FormData, FormInputNode, FormMessages } from "./composables/useFormState";
import { useFormState } from "./composables/useFormState";

import FormInputs from "./FormInputs.vue";

interface Props {
    id?: string;
    inputs: FormInputNode[];
    errors?: FormMessages | null;
    loading?: boolean;
    prefix?: string;
    sustainRepeats?: boolean;
    sustainConditionals?: boolean;
    collapsedEnableText?: string;
    collapsedDisableText?: string;
    collapsedEnableIcon?: IconDefinition;
    collapsedDisableIcon?: IconDefinition;
    validationScrollTo?: [string, string] | null;
    replaceParams?: Record<string, unknown> | null;
    warnings?: FormMessages | null;
    workflowBuildingMode?: boolean;
    workflowRun?: boolean;
    allowEmptyValueOnRequiredInput?: boolean;
    activeNodeId?: number;
    syncWithGraph?: boolean;
    stepsNotMatchingRequest?: string[];
}

const props = withDefaults(defineProps<Props>(), {
    errors: null,
    loading: false,
    prefix: "",
    sustainRepeats: false,
    sustainConditionals: false,
    collapsedEnableText: "Enable",
    collapsedDisableText: "Disable",
    collapsedEnableIcon: () => faCaretSquareDown,
    collapsedDisableIcon: () => faCaretSquareUp,
    validationScrollTo: null,
    replaceParams: null,
    warnings: null,
    workflowBuildingMode: false,
    workflowRun: false,
    allowEmptyValueOnRequiredInput: false,
    syncWithGraph: false,
});

const emit = defineEmits<{
    (e: "onChange", formData: FormData, refreshOnChange?: boolean): void;
    (e: "onValidation", validation: [string, string] | null): void;
    (e: "stop-flagging"): void;
    (e: "update:active-node-id", id: number): void;
}>();

const {
    formInputs,
    formData,
    validation,
    cloneInputs,
    rebuildIndex,
    buildFormData,
    syncServerAttributes,
    applyErrors,
    applyWarnings,
    setError,
    resetErrors,
    replaceParams: doReplaceParams,
} = useFormState({
    allowEmptyValueOnRequiredInput: toRef(props, "allowEmptyValueOnRequiredInput"),
});

// getCurrentInstance is fragile but required in Vue 2.7 Composition API
// to access $el for scrollToElement. Acceptable given the constraint.
const instance = getCurrentInstance();

function onChange(refreshOnChange?: boolean): void {
    rebuildIndex();
    const params = buildFormData();
    if (JSON.stringify(params) != JSON.stringify(formData.value)) {
        formData.value = params;
        resetErrors();
        emit("onChange", params, refreshOnChange);
    }
}

function onChangeForm(): void {
    onChange(true);
}

function onHighlight(val: [string, string] | null | undefined, silent = false): void {
    if (val && val.length == 2) {
        const inputId = val[0];
        const message = val[1];
        setError(inputId, message);
        if (!silent && inputId) {
            scrollToElement(inputId);
        }
    }
}

function scrollToElement(elementId: string | number): void {
    const el = instance?.proxy?.$el?.querySelector(`[id='form-element-${elementId}']`);
    if (el) {
        const centerPanel = document.querySelector("#center");
        if (centerPanel) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            if (props.syncWithGraph && props.activeNodeId !== elementId) {
                updateActiveNode(elementId as number);
            }
        }
    }
}

function updateActiveNode(activeNodeId: number): void {
    emit("update:active-node-id", activeNodeId);
}

// --- Initialization (replaces created() hook) ---
// Bootstrap: runs during setup before watchers are active.
// Emits initial formData so the parent has submittable data immediately.
cloneInputs(props.inputs);
formData.value = buildFormData();
emit("onChange", formData.value);
applyWarnings(props.warnings);
applyErrors(props.errors);

// --- Watchers ---
// All watchers use flush: "sync" to match Options API synchronous watcher timing.
// This ensures attribute sync, error application, and formData emission happen
// in the same tick as the prop change. Performance note: sync flush bypasses
// Vue's batching; acceptable here since these watchers do lightweight work.
watch(
    () => props.activeNodeId,
    () => {
        if (props.activeNodeId != null) {
            scrollToElement(props.activeNodeId);
        }
    },
);

watch(
    () => props.id,
    () => {
        cloneInputs(props.inputs);
        formData.value = buildFormData();
        emit("onChange", formData.value);
        applyWarnings(props.warnings);
        applyErrors(props.errors);
    },
);

watch(
    () => props.inputs,
    () => {
        syncServerAttributes(props.inputs);
        onChangeForm();
    },
    { flush: "sync" },
);

watch(
    () => props.validationScrollTo,
    () => {
        onHighlight(props.validationScrollTo);
    },
    { flush: "sync" },
);

watch(
    validation,
    () => {
        onHighlight(validation.value, true);
        emit("onValidation", validation.value);
    },
    { flush: "sync" },
);

watch(
    () => props.errors,
    () => {
        applyErrors(props.errors);
    },
    { flush: "sync" },
);

watch(
    () => props.replaceParams,
    () => {
        if (props.replaceParams) {
            const refreshOnChange = doReplaceParams(props.replaceParams);
            onChange(refreshOnChange);
        }
    },
    { flush: "sync" },
);

watch(
    () => props.warnings,
    () => {
        applyWarnings(props.warnings);
    },
    { flush: "sync" },
);
</script>
