<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretSquareDown, faCaretSquareUp } from "@fortawesome/free-regular-svg-icons";
import { faArrowsAltH, faExclamation, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { sanitize } from "dompurify";
import type { ComputedRef } from "vue";
import { computed, ref } from "vue";

import { linkify } from "@/utils/utils";

import { isDataUri } from "./Elements/FormData/types";
import type { FormParameterAttributes, FormParameterTypes, FormParameterValue } from "./parameterTypes";

import FormBoolean from "./Elements/FormBoolean.vue";
import FormColor from "./Elements/FormColor.vue";
import FormData from "./Elements/FormData/FormData.vue";
import FormDataUri from "./Elements/FormData/FormDataUri.vue";
import FormDirectory from "./Elements/FormDirectory.vue";
import FormDrilldown from "./Elements/FormDrilldown/FormDrilldown.vue";
import FormError from "./Elements/FormError.vue";
import FormHidden from "./Elements/FormHidden.vue";
import FormInput from "./Elements/FormInput.vue";
import FormNumber from "./Elements/FormNumber.vue";
import FormOptionalText from "./Elements/FormOptionalText.vue";
import FormRulesEdit from "./Elements/FormRulesEdit.vue";
import FormSelection from "./Elements/FormSelection.vue";
import FormTags from "./Elements/FormTags.vue";
import FormText from "./Elements/FormText.vue";
import FormUpload from "./Elements/FormUpload.vue";
import FormElementHeader from "./FormElementHeader.vue";
import FormElementHelpMarkdown from "./FormElementHelpMarkdown.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const TYPE_TO_PLACEHOLDER: Record<string, string> = {
    text: "text input",
    integer: "an integer",
    float: "a floating point number",
};

interface FormElementProps {
    id?: string;
    type: FormParameterTypes | undefined;
    value: FormParameterValue;
    title: string | undefined;
    refreshOnChange?: boolean;
    help: string | undefined;
    helpFormat?: string;
    error: string | undefined;
    warning: string | undefined;
    disabled?: boolean;
    loading?: boolean;
    attributes?: FormParameterAttributes;
    collapsedEnableText?: string;
    collapsedDisableText?: string;
    collapsedEnableIcon?: string;
    collapsedDisableIcon?: string;
    connectedEnableText?: string;
    connectedDisableText?: string;
    connectedEnableIcon?: string;
    connectedDisableIcon?: string;
    workflowBuildingMode?: boolean;
    /** If true, this element is part of a workflow run form. */
    workflowRun?: boolean;
}

const props = withDefaults(defineProps<FormElementProps>(), {
    id: "identifier",
    refreshOnChange: false,
    disabled: false,
    collapsedEnableText: "Enable",
    collapsedDisableText: "Disable",
    collapsedEnableIcon: "far fa-caret-square-down",
    collapsedDisableIcon: "far fa-caret-square-up",
    connectedEnableText: "Remove connection from module.",
    connectedDisableText: "Add connection to module.",
    connectedEnableIcon: "fa fa-times",
    connectedDisableIcon: "fa fa-arrows-alt-h",
    helpFormat: "html",
    workflowBuildingMode: false,
    workflowRun: false,
    attributes: () => ({}),
});

const emit = defineEmits<{
    (e: "input", value: FormParameterValue, id: string): void;
    (e: "change", shouldRefresh: boolean): void;
}>();

library.add(faExclamation, faTimes, faArrowsAltH, faCaretSquareDown, faCaretSquareUp);

const collapsibleValue: ComputedRef<FormParameterValue> = computed(() => props.attributes.collapsible_value);
const defaultValue: ComputedRef<FormParameterValue> = computed(() => props.attributes.default_value);
const connectedValue: FormParameterValue = { __class__: "ConnectedValue" };

const computedPlaceholder = computed(() => {
    if (!props.workflowRun) {
        return "";
    }
    if (props.attributes.placeholder || !props.type) {
        return props.attributes.placeholder;
    }
    return `please provide ${props.type in TYPE_TO_PLACEHOLDER ? TYPE_TO_PLACEHOLDER[props.type] : "a value"}${
        isOptional.value ? " (optional)" : ""
    }`;
});

/** In the case this is an element in a workflow run form, this is true
 * when the element is unpopulated and the only alert is the unpopulated error.
 */
const unPopulatedError = computed(
    () =>
        props.workflowRun && alerts.value?.length === 1 && alerts.value[0] === "Please provide a value for this option."
);

const connected = ref(false);
const collapsed = ref(false);

const collapsible = computed(() => !props.disabled && collapsibleValue.value !== undefined);
const connectable = computed(() => collapsible.value && Boolean(props.attributes.connectable));

// Determines whether to expand or collapse the input
{
    const valueJson = JSON.stringify(props.value);
    connected.value = valueJson === JSON.stringify(connectedValue);
    collapsed.value =
        connected.value ||
        (collapsibleValue.value !== undefined && valueJson === JSON.stringify(collapsibleValue.value));
}

/** Submits a changed value. */
function setValue(value: FormParameterValue) {
    emit("input", value, props.id);
    emit("change", props.refreshOnChange);
}

/** Handles collapsible toggle. */
function onCollapse() {
    collapsed.value = !collapsed.value;
    connected.value = false;
    if (collapsed.value) {
        setValue(collapsibleValue.value);
    } else {
        setValue(defaultValue.value);
    }
}

/** Handles connected state. */
function onConnect() {
    connected.value = !connected.value;
    collapsed.value = connected.value;
    if (connected.value) {
        setValue(connectedValue);
    } else {
        setValue(defaultValue.value);
    }
}

const isHidden = computed(() => props.attributes.hidden);
const elementId = computed(() => `form-element-${props.id}`);
const hasAlert = computed(() => alerts.value.length > 0);
const showPreview = computed(() => (collapsed.value && props.attributes.collapsible_preview) || props.disabled);
const showField = computed(() => !collapsed.value && !props.disabled);
const formDataField = computed(() =>
    props.type && ["data", "data_collection"].includes(props.type) ? (props.type as "data" | "data_collection") : null
);
const isUriDataField = computed(() => formDataField.value && isDataUri(props.value));

const previewText = computed(() => props.attributes.text_value);
const helpText = computed(() => {
    const helpArgument = props.attributes.argument;
    if (helpArgument && !props.help?.includes(`(${helpArgument})`)) {
        return `${props.help} (${helpArgument})`;
    } else {
        return props.help;
    }
});
const nonMdHelp = computed(() =>
    Boolean(helpText.value) && props.helpFormat != "markdown" && (!props.workflowRun || helpText.value !== props.title)
        ? sanitize(helpText.value!)
        : ""
);
const showNonMdHelp = computed(() => Boolean(nonMdHelp.value) && (!props.workflowRun || props.type !== "boolean"));

// TODO: Replace nay cast with template casts
// the any cast is a work around for vue 2
// once upgraded to vue 3, remove this `any`,
// and use type casts in the template
const currentValue = computed<any>({
    get() {
        return props.value ?? props.attributes.value;
    },
    set(val) {
        setValue(val);
    },
});

// TODO: Remove
// the any cast is a work around for vue 2
// once upgraded to vue 3, remove this computed,
// and use type casts in the template
const attributeOptions = computed<any>(() => props.attributes.options);

/**
 * Instead of just using `props.title`, we check `attrs.label` and `attrs.name`:
 *
 * If `attrs.label` is an integer, and `attrs.name = attrs.label - 1`, then we
 * can infer the user didn't provide a title, and we had just set the title/label
 * to the step index + 1.
 */
const userDefinedTitle = computed(() => {
    const label = parseInt(props.attributes.label ?? "");
    const name = parseInt(props.attributes.name ?? "");
    if (isNaN(label) || isNaN(name) || name !== label - 1) {
        return props.title;
    }
    return undefined;
});

const isHiddenType = computed(
    () =>
        ["hidden", "hidden_data", "baseurl"].includes(props.type ?? "") ||
        (props.attributes && props.attributes.titleonly)
);

/** Determines if the element renders content below the title. */
const rendersContent = computed(
    () =>
        (props.workflowRun && hasAlert.value && !unPopulatedError.value) ||
        showField.value ||
        showPreview.value ||
        helpText.value
);

const collapseText = computed(() => (collapsed.value ? props.collapsedEnableText : props.collapsedDisableText));
const connectText = computed(() => (connected.value ? props.connectedEnableText : props.connectedDisableText));

const isEmpty = computed(() => {
    if (currentValue.value === null || currentValue.value === undefined) {
        return true;
    }

    if (["text", "integer", "float", "password"].includes(props.type ?? "") && currentValue.value === "") {
        return true;
    }

    return false;
});

const isRequired = computed(() => props.attributes.optional === false);
const isRequiredType = computed(() => props.type !== "boolean");
const isOptional = computed(() => !isRequired.value && props.attributes.optional !== undefined);
const formAlert = ref<string>();
const alerts = computed(() => {
    return [formAlert.value, props.error, props.warning]
        .filter((v) => v !== undefined && v !== null)
        .map((v) => linkify(sanitize(v!, { USE_PROFILES: { html: true } })));
});

/** Adds a temporary 2 sec focus to the element. */
function addTempFocus() {
    const element = document.getElementById(elementId.value);
    if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
        element.classList.add("temp-focus");
        setTimeout(() => {
            element.classList.remove("temp-focus");
        }, 2000);
    }
}

function onAlert(value: string | undefined) {
    formAlert.value = value;
}
</script>

<template>
    <div
        v-show="!isHidden"
        :id="elementId"
        class="ui-form-element section-row"
        :class="{
            alert: hasAlert || props.workflowRun,
            'alert-info': hasAlert && !props.workflowRun,
            'workflow-run-element p-0': props.workflowRun,
        }">
        <FormError v-if="hasAlert && !props.workflowRun" :alerts="alerts" />

        <div class="ui-form-title" :class="{ 'card-header m-0 px-3 py-2': props.workflowRun }">
            <div>
                <span v-if="collapsible || connectable">
                    <GButton
                        v-if="collapsible && !connected"
                        color="blue"
                        tooltip
                        transparent
                        inline
                        icon-only
                        data-collapsible
                        :title="collapseText"
                        @click="onCollapse">
                        <FontAwesomeIcon v-if="collapsed" fixed-with :icon="props.collapsedEnableIcon" />
                        <FontAwesomeIcon v-else fixed-with :icon="props.collapsedDisableIcon" />
                    </GButton>

                    <GButton
                        v-if="connectable"
                        color="blue"
                        tooltip
                        transparent
                        inline
                        icon-only
                        data-connected
                        :title="connectText"
                        @click="onConnect">
                        <FontAwesomeIcon v-if="connected" fixed-with :icon="props.connectedEnableIcon" />
                        <FontAwesomeIcon v-else fixed-with :icon="props.connectedDisableIcon" />
                    </GButton>

                    <span v-if="props.title" class="ui-form-title-text ml-1">
                        <label :for="props.id">{{ props.title }}</label>
                    </span>
                </span>
                <span v-else-if="props.title" class="ui-form-title-text">
                    <label :for="props.id">{{ props.title }}</label>
                </span>

                <span
                    v-if="isRequired && isRequiredType && props.title"
                    v-b-tooltip.hover
                    class="ui-form-title-star"
                    title="required"
                    :class="{ warning: isEmpty }">
                    *
                    <span v-if="isEmpty" class="ui-form-title-message warning"> required </span>
                </span>
                <span v-else-if="isOptional && isRequiredType && props.title" class="ui-form-title-message">
                    - optional
                </span>
            </div>
            <FormElementHeader
                v-if="props.workflowRun"
                :id="props.id"
                :type="props.type"
                :has-alert="hasAlert"
                :is-empty="isEmpty"
                :is-optional="isOptional"
                :extensions="props.attributes.extensions">
                <template v-slot:badges>
                    <slot name="workflow-run-form-title-badges" />
                </template>
                <template v-slot:action-items>
                    <slot name="workflow-run-form-title-items" />
                </template>
            </FormElementHeader>
        </div>

        <div v-if="rendersContent" :class="{ 'form-element-content px-3 py-1 mb-2': props.workflowRun }">
            <FormError v-if="props.workflowRun && hasAlert && !unPopulatedError" :alerts="alerts" has-alert-class />

            <div v-if="showField" class="ui-form-field" :data-label="props.title">
                <div
                    v-if="props.type === 'boolean' && props.workflowRun"
                    :class="{ 'd-flex align-items-start flex-gapx-1': Boolean(nonMdHelp) }">
                    <FormBoolean :id="props.id" v-model="currentValue" class="mr-2" :no-label="Boolean(nonMdHelp)" />
                    <!-- eslint-disable-next-line vue/no-v-html -->
                    <span v-if="Boolean(nonMdHelp)" class="text-muted" v-html="nonMdHelp" />
                </div>
                <FormBoolean v-else-if="props.type === 'boolean'" :id="props.id" v-model="currentValue" />
                <FormHidden
                    v-else-if="isHiddenType"
                    :id="props.id"
                    v-model="currentValue"
                    :info="props.attributes.info" />
                <FormNumber
                    v-else-if="props.type === 'integer' || props.type === 'float'"
                    :id="props.id"
                    v-model="currentValue"
                    :max="props.attributes.max"
                    :min="props.attributes.min"
                    :placeholder="computedPlaceholder"
                    :optional="isOptional"
                    :show-state="props.workflowRun"
                    :type="props.type ?? 'float'"
                    :workflow-building-mode="workflowBuildingMode" />
                <FormOptionalText
                    v-else-if="props.type === 'select' && props.attributes.is_workflow && props.attributes.optional"
                    :id="props.id"
                    v-model="currentValue"
                    :readonly="props.attributes.readonly"
                    :area="props.attributes.area"
                    :placeholder="computedPlaceholder"
                    :multiple="props.attributes.multiple"
                    :datalist="props.attributes.datalist"
                    :type="props.type" />
                <FormText
                    v-else-if="
                        ['text', 'password'].includes(props.type ?? '') ||
                        (props.attributes.is_workflow &&
                            ['data_column', 'drill_down', 'genomebuild', 'group_tag', 'select'].includes(
                                props.type ?? ''
                            ))
                    "
                    :id="props.id"
                    v-model="currentValue"
                    :readonly="props.attributes.readonly"
                    :area="props.attributes.area"
                    :placeholder="computedPlaceholder"
                    :optional="isOptional"
                    :show-state="props.workflowRun"
                    :color="props.attributes.color"
                    :multiple="props.attributes.multiple"
                    :cls="props.attributes.cls"
                    :datalist="props.attributes.datalist"
                    :type="props.type" />
                <FormSelection
                    v-else-if="
                        (props.type === undefined && props.attributes.options) ||
                        ['data_column', 'genomebuild', 'group_tag', 'select'].includes(props.type ?? '')
                    "
                    :id="props.id"
                    v-model="currentValue"
                    :data="props.attributes.data"
                    :display="props.attributes.display"
                    :options="attributeOptions"
                    :optional="props.attributes.optional"
                    :multiple="props.attributes.multiple" />
                <FormDataUri v-else-if="isUriDataField" :id="props.id" :multiple="props.attributes.multiple" />
                <FormData
                    v-else-if="formDataField"
                    :id="props.id"
                    v-model="currentValue"
                    :loading="loading"
                    :extensions="props.attributes.extensions"
                    :flavor="props.attributes.flavor"
                    :multiple="props.attributes.multiple"
                    :optional="props.attributes.optional"
                    :options="attributeOptions"
                    :tag="props.attributes.tag"
                    :user-defined-title="userDefinedTitle"
                    :type="formDataField"
                    :collection-types="props.attributes.collection_types"
                    :workflow-run="props.workflowRun"
                    @alert="onAlert"
                    @focus="addTempFocus" />
                <FormDrilldown
                    v-else-if="props.type === 'drill_down'"
                    :id="props.id"
                    v-model="currentValue"
                    :options="attributeOptions"
                    :multiple="props.attributes.multiple" />
                <FormColor v-else-if="props.type === 'color'" :id="props.id" v-model="currentValue" />
                <FormDirectory v-else-if="props.type === 'directory_uri'" v-model="currentValue" />
                <FormUpload v-else-if="props.type === 'upload'" v-model="currentValue" />
                <FormRulesEdit
                    v-else-if="props.type == 'rules'"
                    v-model="currentValue"
                    :target="props.attributes.target" />
                <FormTags
                    v-else-if="props.type === 'tags'"
                    v-model="currentValue"
                    :placeholder="props.attributes?.placeholder" />
                <FormInput v-else :id="props.id" v-model="currentValue" :area="props.attributes.area" />
            </div>

            <div v-if="showPreview" class="ui-form-preview pt-1 pl-2 mt-1">{{ previewText }}</div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <span v-if="showNonMdHelp" class="ui-form-info form-text text-muted" v-html="nonMdHelp" />
            <span v-else-if="Boolean(helpText) && helpFormat === 'markdown'" class="ui-form-info form-text text-muted">
                <FormElementHelpMarkdown :content="helpText ?? ''" />
            </span>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "./_form-elements.scss";
@import "base.scss";

// Workflow Run Form
.workflow-run-element {
    // when a temporary focus is applied to the element
    &.temp-focus {
        border: solid 3px $brand-primary;
    }
    &:not(.temp-focus) {
        border: solid 1px $portlet-bg-color;
        box-shadow: 0 0 5px $portlet-bg-color;
    }

    .ui-form-title {
        display: flex;
        align-items: center;
        justify-content: space-between;

        // inherit the border radius from the parent .alert class
        border-top-left-radius: inherit;
        border-top-right-radius: inherit;

        &:deep(.form-element-header-badge) {
            display: flex;
            align-items: center;
            font-weight: normal;
            font-size: 100%;
            padding-left: $spacer;
            padding-right: $spacer;

            &.populated {
                background-color: $state-success-bg;
            }
            &.unpopulated {
                background-color: $state-info-bg;
            }
        }
    }
    .form-element-content {
        display: flex;
        flex-direction: column;
        row-gap: 0.25rem;

        .ui-form-info {
            order: -1;
        }
    }
}
</style>
