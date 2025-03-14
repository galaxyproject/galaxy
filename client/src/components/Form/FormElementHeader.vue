<script setup lang="ts">
import { faCheck, faExclamation, faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { computed, ref } from "vue";

import { useUid } from "@/composables/utils/uid";

import type { FormParameterTypes } from "./parameterTypes";

import FormDataExtensions from "./Elements/FormData/FormDataExtensions.vue";

const props = defineProps<{
    type?: FormParameterTypes;
    hasAlert: boolean;
    id: string;
    isEmpty: boolean;
    isOptional: boolean;
    extensions?: string[];
}>();

// Rendering formats
const formatsVisible = ref(false);
const formatsButtonId = useUid("form-element-formats-");
const renderFormats = computed(
    () =>
        props.type &&
        ["data", "data_collection"].includes(props.type) &&
        props.extensions?.length &&
        props.extensions.indexOf("data") < 0
);

const populatedClass = computed<string>(() => {
    if (props.hasAlert || (props.isEmpty && !props.isOptional)) {
        return "unpopulated";
    } else if (!props.isEmpty) {
        return "populated";
    }
    return "";
});

const badgeData = computed(() => {
    switch (true) {
        case props.hasAlert:
            return { icon: faExclamation, class: "text-danger", message: "Fix error(s) for this step" };
        case props.isEmpty && !props.isOptional:
            return { icon: faExclamationCircle, message: "Provide a value for this step" };
        case !props.isEmpty:
            return { icon: faCheck, class: "text-success", message: "Step is populated" };
        default:
            return {};
    }
});
</script>

<template>
    <div class="d-flex align-items-center flex-gapx-1">
        <FormDataExtensions
            v-if="renderFormats"
            class="mr-1"
            popover
            minimal
            :extensions="props.extensions || []"
            :formats-button-id="formatsButtonId"
            :formats-visible.sync="formatsVisible" />
        <BBadge
            v-if="badgeData.message && props.type !== 'boolean'"
            v-b-tooltip.hover.noninteractive
            class="flex-gapx-1 form-element-header-badge"
            :class="populatedClass"
            :title="badgeData.message">
            <FontAwesomeIcon v-if="badgeData?.icon" :icon="badgeData.icon" :class="badgeData.class" fixed-width />
        </BBadge>
        <slot name="form-element" />
        <slot name="action-items" />
    </div>
</template>
