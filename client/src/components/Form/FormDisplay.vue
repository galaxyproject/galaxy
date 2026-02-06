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

<script setup>
import { faCaretSquareDown, faCaretSquareUp } from "@fortawesome/free-regular-svg-icons";
import { getCurrentInstance, toRef, watch } from "vue";

import { useFormState } from "./composables/useFormState";

import FormInputs from "./FormInputs.vue";

const props = defineProps({
    id: {
        type: String,
        default: null,
    },
    inputs: {
        type: Array,
        required: true,
    },
    errors: {
        type: Object,
        default: null,
    },
    loading: {
        type: Boolean,
        default: false,
    },
    prefix: {
        type: String,
        default: "",
    },
    sustainRepeats: {
        type: Boolean,
        default: false,
    },
    sustainConditionals: {
        type: Boolean,
        default: false,
    },
    collapsedEnableText: {
        type: String,
        default: "Enable",
    },
    collapsedDisableText: {
        type: String,
        default: "Disable",
    },
    collapsedEnableIcon: {
        type: Object,
        default: () => faCaretSquareDown,
    },
    collapsedDisableIcon: {
        type: Object,
        default: () => faCaretSquareUp,
    },
    validationScrollTo: {
        type: Array,
        default: null,
    },
    replaceParams: {
        type: Object,
        default: null,
    },
    warnings: {
        type: Object,
        default: null,
    },
    workflowBuildingMode: {
        type: Boolean,
        default: false,
    },
    workflowRun: {
        type: Boolean,
        default: false,
    },
    allowEmptyValueOnRequiredInput: {
        type: Boolean,
        default: false,
    },
    activeNodeId: {
        type: Number,
        default: null,
    },
    syncWithGraph: {
        type: Boolean,
        default: false,
    },
    stepsNotMatchingRequest: {
        type: Array,
        default: null,
    },
});

const emit = defineEmits(["onChange", "onValidation", "stop-flagging", "update:active-node-id"]);

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

const instance = getCurrentInstance();

function onChange(refreshOnChange) {
    rebuildIndex();
    const params = buildFormData();
    if (JSON.stringify(params) != JSON.stringify(formData.value)) {
        resetErrors();
        emit("onChange", formData.value, refreshOnChange);
    }
}

function onChangeForm() {
    onChange(true);
}

function onHighlight(val, silent = false) {
    if (val && val.length == 2) {
        const inputId = val[0];
        const message = val[1];
        setError(inputId, message);
        if (!silent && inputId) {
            scrollToElement(inputId);
        }
    }
}

function scrollToElement(elementId) {
    const el = instance?.proxy?.$el?.querySelector(`[id='form-element-${elementId}']`);
    if (el) {
        const centerPanel = document.querySelector("#center");
        if (centerPanel) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            if (props.syncWithGraph && props.activeNodeId !== elementId) {
                updateActiveNode(elementId);
            }
        }
    }
}

function updateActiveNode(activeNodeId) {
    emit("update:active-node-id", activeNodeId);
}

// --- Initialization (replaces created() hook) ---
cloneInputs(props.inputs);
buildFormData();
emit("onChange", formData.value);
applyWarnings(props.warnings);
applyErrors(props.errors);

// --- Watchers ---
watch(
    () => props.activeNodeId,
    () => {
        scrollToElement(props.activeNodeId);
    }
);

watch(
    () => props.id,
    () => {
        cloneInputs(props.inputs);
        buildFormData();
        emit("onChange", formData.value);
        applyWarnings(props.warnings);
        applyErrors(props.errors);
    }
);

watch(
    () => props.inputs,
    () => {
        syncServerAttributes(props.inputs);
        onChangeForm();
    },
    { flush: "sync" }
);

watch(
    () => props.validationScrollTo,
    () => {
        onHighlight(props.validationScrollTo);
    },
    { flush: "sync" }
);

watch(validation, () => {
    onHighlight(validation.value, true);
    emit("onValidation", validation.value);
}, { flush: "sync" });

watch(
    () => props.errors,
    () => {
        applyErrors(props.errors);
    },
    { flush: "sync" }
);

watch(
    () => props.replaceParams,
    () => {
        const refreshOnChange = doReplaceParams(props.replaceParams);
        onChange(refreshOnChange);
    },
    { flush: "sync" }
);

watch(
    () => props.warnings,
    () => {
        applyWarnings(props.warnings);
    },
    { flush: "sync" }
);
</script>
