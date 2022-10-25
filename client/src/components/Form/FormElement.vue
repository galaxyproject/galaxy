<script setup>
import _ from "underscore";
import FormBoolean from "./Elements/FormBoolean";
import FormHidden from "./Elements/FormHidden";
import FormInput from "./Elements/FormInput";
import FormParameter from "./Elements/FormParameter";
import FormColor from "./Elements/FormColor";
import FormDirectory from "./Elements/FormDirectory";
import FormNumber from "./Elements/FormNumber";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, computed, useAttrs } from "vue";

const props = defineProps({
    id: {
        type: String,
        default: "identifier",
    },
    type: {
        type: String,
        default: null,
    },
    value: {
        default: null,
    },
    title: {
        type: String,
        default: null,
    },
    refreshOnChange: {
        type: Boolean,
        default: false,
    },
    help: {
        type: String,
        default: null,
    },
    error: {
        type: String,
        default: null,
    },
    backbonejs: {
        type: Boolean,
        default: false,
    },
    disabled: {
        type: Boolean,
        default: false,
    },
    attributes: {
        type: Object,
        default: null,
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
        type: String,
        default: "far fa-caret-square-down",
    },
    collapsedDisableIcon: {
        type: String,
        default: "far fa-caret-square-up",
    },
    connectedEnableText: {
        type: String,
        default: "Remove connection from module.",
    },
    connectedDisableText: {
        type: String,
        default: "Add connection to module.",
    },
    connectedEnableIcon: {
        type: String,
        default: "fa fa-times",
    },
    connectedDisableIcon: {
        type: String,
        default: "fa fa-arrows-alt-h",
    },
    workflowBuildingMode: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(["input", "change"]);

const attrs = computed(() => props.attributes || useAttrs());
const collapsibleValue = computed(() => attrs.value["collapsible_value"]);
const defaultValue = computed(() => attrs.value["default_value"]);
const connectedValue = { __class__: "ConnectedValue" };

const connected = ref(false);
const collapsed = ref(false);

const collapsible = computed(() => !props.disabled && collapsibleValue.value !== undefined);
const connectable = computed(() => collapsible.value && attrs.value["connectable"]);

// Determines to wether expand or collapse the input
{
    setValue(props.value);
    const valueJson = JSON.stringify(props.value);
    connected.value = valueJson === JSON.stringify(connectedValue);
    collapsed.value =
        connected.value ||
        (collapsibleValue.value !== undefined && valueJson === JSON.stringify(collapsibleValue.value));
}

/** Submits a changed value. */
function setValue(value) {
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
const hasError = computed(() => Boolean(props.error));
const showPreview = computed(() => (collapsed.value && attrs.value["collapsible_preview"]) || props.disabled);

const previewText = computed(() => _.escape(this.textValue).replace(/\n/g, "<br>"));
const helpText = computed(() => {
    const helpArgument = attrs.value["argument"];
    if (helpArgument && !props.help.includes(`(${helpArgument})`)) {
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
    () => ["hidden", "hidden_data", "baseurl"].includes(props.type) || (props.attributes && props.attributes.titleonly)
);

const collapseText = computed(() => (collapsed.value ? props.collapsedEnableText : props.collapsedDisableText));
const connectText = computed(() => (connected.value ? props.connectedEnableText : props.connectedDisableText));
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExclamation, faTimes, faArrowsAltH } from "@fortawesome/free-solid-svg-icons";
import { faCaretSquareDown, faCaretSquareUp } from "@fortawesome/free-regular-svg-icons";

library.add(faExclamation, faTimes, faArrowsAltH, faCaretSquareDown, faCaretSquareUp);
</script>

<template>
    <div
        v-show="!isHidden"
        :id="elementId"
        class="ui-form-element section-row"
        :class="{ alert: hasError, 'alert-info': hasError }">
        <div v-if="hasError" class="ui-form-error">
            <FontAwesomeIcon class="mr-1" icon="fa-exclamation" />
            <span class="ui-form-error-text" v-html="props.error" />
        </div>

        <div v-if="props.title" class="ui-form-title">
            <div v-if="collapsible || connectable">
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

                <span class="ui-form-title-text ml-1">
                    {{ props.title }}
                </span>
            </div>
            <span v-else class="ui-form-title-text">{{ props.title }}</span>
        </div>

        <div v-if="!collapsed && !disabled" class="ui-form-field" :data-label="props.title">
            <FormBoolean v-if="props.type === 'boolean'" :id="props.id" v-model="currentValue" />
            <FormHidden v-else-if="isHiddenType" :id="props.id" v-model="currentValue" :info="attrs['info']" />
            <FormNumber
                v-else-if="props.type === 'integer' || props.type === 'float'"
                :id="props.id"
                v-model="currentValue"
                :max="attrs.max"
                :min="attrs.min"
                :type="type"
                :workflow-building-mode="workflowBuildingMode" />
            <FormColor v-else-if="props.type === 'color'" :id="props.id" v-model="currentValue" />
            <FormDirectory v-else-if="props.type === 'directory_uri'" v-model="currentValue" />
            <FormParameter
                v-else-if="backbonejs"
                :id="props.id"
                v-model="currentValue"
                :data-label="props.title"
                :type="props.type"
                :attributes="attrs" />
            <FormInput v-else :id="props.id" v-model="currentValue" :area="attrs['area']" />
        </div>

        <div v-if="showPreview" class="ui-form-preview" v-html="previewText" />
        <span v-if="Boolean(helpText)" class="ui-form-info form-text text-muted" v-html="helpText" />
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.ui-form-element {
    &:deep(.ui-form-collapsible-icon),
    &:deep(.ui-form-connected-icon) {
        border: none;
        background: none;
        padding: 0;
        line-height: 1;
        font-size: 1.2em;

        &:hover {
            color: $brand-info;
        }

        &:focus {
            color: $brand-primary;
        }

        &:active {
            background: none;
        }
    }
}
</style>
