<script setup lang="ts">
import { faCheck, faExclamation, faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { computed } from "vue";

import type { FormParameterTypes } from "./parameterTypes";

const props = defineProps<{
    type?: FormParameterTypes;
    hasAlert: boolean;
    id: string;
    isEmpty: boolean;
    isOptional: boolean;
}>();

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
        <slot name="badges" />
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
