<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretSquareDown, faCaretSquareUp } from "@fortawesome/free-regular-svg-icons";
import { faArrowsAltH, faExclamation, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { sanitize } from "dompurify";
import type { ComputedRef } from "vue";
import { computed, ref, useAttrs } from "vue";

import { linkify } from "@/utils/utils";

import type { FormParameterAttributes, FormParameterTypes, FormParameterValue } from "./parameterTypes";

import FormBoolean from "./Elements/FormBoolean.vue";
import FormColor from "./Elements/FormColor.vue";
import FormData from "./Elements/FormData/FormData.vue";
import FormDataUri from "./Elements/FormData/FormDataUri.vue";
import FormDataDialog from "./Elements/FormDataDialog.vue";
import FormDirectory from "./Elements/FormDirectory.vue";
import FormDrilldown from "./Elements/FormDrilldown/FormDrilldown.vue";
import FormHidden from "./Elements/FormHidden.vue";
import FormInput from "./Elements/FormInput.vue";
import FormNumber from "./Elements/FormNumber.vue";
import FormOptionalText from "./Elements/FormOptionalText.vue";
import FormRulesEdit from "./Elements/FormRulesEdit.vue";
import FormSelection from "./Elements/FormSelection.vue";
import FormTags from "./Elements/FormTags.vue";
import FormText from "./Elements/FormText.vue";
import FormUpload from "./Elements/FormUpload.vue";
import FormElementHelpMarkdown from "./FormElementHelpMarkdown.vue";

interface FormElementProps {
    id?: string;
    type?: FormParameterTypes;
    value?: FormParameterValue;
    title?: string;
    refreshOnChange?: boolean;
    help?: string;
    helpFormat?: string;
    error?: string;
    warning?: string;
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
});

const emit = defineEmits<{
    (e: "input", value: FormParameterValue, id: string): void;
    (e: "change", shouldRefresh: boolean): void;
}>();

library.add(faExclamation, faTimes, faArrowsAltH, faCaretSquareDown, faCaretSquareUp);

/** TODO: remove attrs computed.
 useAttrs is *not* reactive, and does not play nice with type safety.
 It is present for compatibility with the legacy "FormParameter" component,
 but should be removed as soon as that component is removed.
 */
const attrs: ComputedRef<FormParameterAttributes> = computed(() => props.attributes || useAttrs());
const collapsibleValue: ComputedRef<FormParameterValue> = computed(() => attrs.value["collapsible_value"]);
const defaultValue: ComputedRef<FormParameterValue> = computed(() => attrs.value["default_value"]);
const connectedValue: FormParameterValue = { __class__: "ConnectedValue" };

const connected = ref(false);
const collapsed = ref(false);

const collapsible = computed(() => !props.disabled && collapsibleValue.value !== undefined);
const connectable = computed(() => collapsible.value && Boolean(attrs.value["connectable"]));

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

const isHidden = computed(() => attrs.value["hidden"]);
const elementId = computed(() => `form-element-${props.id}`);
const hasAlert = computed(() => alerts.value.length > 0);
const showPreview = computed(() => (collapsed.value && attrs.value["collapsible_preview"]) || props.disabled);
const showField = computed(() => !collapsed.value && !props.disabled);
const isUriDataField = computed(() => {
    const dataField = props.type == "data";
    if (dataField && props.value && "src" in props.value) {
        const src = props.value.src;
        return src == "url";
    }
    return false;
});

const previewText = computed(() => attrs.value["text_value"]);
const helpText = computed(() => {
    const helpArgument = attrs.value["argument"];
    if (helpArgument && !props.help?.includes(`(${helpArgument})`)) {
        return `${props.help} (${helpArgument})`;
    } else {
        return props.help;
    }
});

const currentValue = computed({
    get() {
        return props.value;
    },
    set(val) {
        setValue(val);
    },
});

const isHiddenType = computed(
    () =>
        ["hidden", "hidden_data", "baseurl"].includes(props.type ?? "") ||
        (props.attributes && props.attributes.titleonly)
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

const isRequired = computed(() => attrs.value["optional"] === false);
const isRequiredType = computed(() => props.type !== "boolean");
const isOptional = computed(() => !isRequired.value && attrs.value["optional"] !== undefined);
const formAlert = ref<string>();
const alerts = computed(() => {
    return [formAlert.value, props.error, props.warning]
        .filter((v) => v !== undefined && v !== null)
        .map((v) => linkify(sanitize(v!, { USE_PROFILES: { html: true } })));
});

function onAlert(value: string | undefined) {
    formAlert.value = value;
}
</script>

<template>
    <div
        v-show="!isHidden"
        :id="elementId"
        class="ui-form-element section-row"
        :class="{ alert: hasAlert, 'alert-info': hasAlert }">
        <div v-for="(alert, index) in alerts" :key="index" class="ui-form-error">
            <FontAwesomeIcon class="mr-1" icon="fa-exclamation" />
            <span class="ui-form-error-text" v-html="alert" />
        </div>

        <div class="ui-form-title">
            <span v-if="collapsible || connectable">
                <b-button
                    v-if="collapsible && !connected"
                    class="ui-form-collapsible-icon"
                    :title="collapseText"
                    @click="onCollapse">
                    <FontAwesomeIcon v-if="collapsed" :icon="props.collapsedEnableIcon" />
                    <FontAwesomeIcon v-else :icon="props.collapsedDisableIcon" />
                </b-button>

                <b-button v-if="connectable" class="ui-form-connected-icon" :title="connectText" @click="onConnect">
                    <FontAwesomeIcon v-if="connected" :icon="props.connectedEnableIcon" />
                    <FontAwesomeIcon v-else :icon="props.connectedDisableIcon" />
                </b-button>

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
        <div v-if="showField" class="ui-form-field" :data-label="props.title">
            <FormBoolean v-if="props.type === 'boolean'" :id="props.id" v-model="currentValue" />
            <FormHidden v-else-if="isHiddenType" :id="props.id" v-model="currentValue" :info="attrs['info']" />
            <FormNumber
                v-else-if="props.type === 'integer' || props.type === 'float'"
                :id="props.id"
                v-model="currentValue"
                :max="attrs.max"
                :min="attrs.min"
                :type="props.type ?? 'float'"
                :workflow-building-mode="workflowBuildingMode" />
            <FormOptionalText
                v-else-if="props.type === 'select' && attrs.is_workflow && attrs.optional"
                :id="id"
                v-model="currentValue"
                :readonly="attrs.readonly"
                :value="attrs.value"
                :area="attrs.area"
                :placeholder="attrs.placeholder"
                :multiple="attrs.multiple"
                :datalist="attrs.datalist"
                :type="props.type" />
            <FormText
                v-else-if="
                    ['text', 'password'].includes(props.type) ||
                    (attrs.is_workflow &&
                        ['data_column', 'drill_down', 'genomebuild', 'group_tag', 'select'].includes(props.type))
                "
                :id="id"
                v-model="currentValue"
                :readonly="attrs.readonly"
                :value="attrs.value"
                :area="attrs.area"
                :placeholder="attrs.placeholder"
                :color="attrs.color"
                :multiple="attrs.multiple"
                :cls="attrs.cls"
                :datalist="attrs.datalist"
                :type="props.type" />
            <FormSelection
                v-else-if="
                    (props.type === undefined && attrs.options) ||
                    ['data_column', 'genomebuild', 'group_tag', 'select'].includes(props.type)
                "
                :id="id"
                v-model="currentValue"
                :data="attrs.data"
                :display="attrs.display"
                :options="attrs.options"
                :optional="attrs.optional"
                :multiple="attrs.multiple" />
            <FormDataUri
                v-else-if="isUriDataField"
                :id="id"
                v-model="currentValue"
                :value="attrs.value"
                :multiple="attrs.multiple" />
            <FormData
                v-else-if="['data', 'data_collection'].includes(props.type)"
                :id="id"
                v-model="currentValue"
                :loading="loading"
                :extensions="attrs.extensions"
                :flavor="attrs.flavor"
                :multiple="attrs.multiple"
                :optional="attrs.optional"
                :options="attrs.options"
                :tag="attrs.tag"
                :type="props.type"
                :collection-types="attrs.collection_types"
                @alert="onAlert" />
            <FormDrilldown
                v-else-if="props.type === 'drill_down'"
                :id="id"
                v-model="currentValue"
                :options="attrs.options"
                :multiple="attrs.multiple" />
            <FormDataDialog
                v-else-if="props.type === 'data_dialog'"
                :id="id"
                v-model="currentValue"
                :multiple="attrs.multiple === 'true'" />
            <FormColor v-else-if="props.type === 'color'" :id="props.id" v-model="currentValue" />
            <FormDirectory v-else-if="props.type === 'directory_uri'" v-model="currentValue" />
            <FormUpload v-else-if="props.type === 'upload'" v-model="currentValue" />
            <FormRulesEdit v-else-if="props.type == 'rules'" v-model="currentValue" :target="attrs.target" />
            <FormTags
                v-else-if="props.type === 'tags'"
                v-model="currentValue"
                :placeholder="props.attributes?.placeholder" />
            <FormInput v-else :id="props.id" v-model="currentValue" :area="attrs['area']" />
        </div>

        <div v-if="showPreview" class="ui-form-preview pt-1 pl-2 mt-1">{{ previewText }}</div>
        <span
            v-if="Boolean(helpText) && helpFormat != 'markdown'"
            class="ui-form-info form-text text-muted"
            v-html="helpText" />
        <span v-else-if="Boolean(helpText)" class="ui-form-info form-text text-muted"
            ><FormElementHelpMarkdown :content="helpText"
        /></span>
    </div>
</template>

<style lang="scss" scoped>
@import "./_form-elements.scss";
</style>
