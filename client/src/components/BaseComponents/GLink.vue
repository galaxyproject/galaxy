<script setup lang="ts">
import type { Placement } from "@popperjs/core";
import { computed, ref } from "vue";
import type { RouterLink } from "vue-router";

import type { ComponentSize } from "@/components/BaseComponents/componentVariants";
import { useClickableElement } from "@/components/BaseComponents/composables/clickableElement";
import { useCurrentTitle } from "@/components/BaseComponents/composables/currentTitle";
import { useResolveElement } from "@/composables/resolveElement";
import { useUid } from "@/composables/utils/uid";

import GTooltip from "@/components/BaseComponents/GTooltip.vue";

const props = defineProps<{
    href?: string;
    to?: string;
    disabled?: boolean;
    title?: string;
    disabledTitle?: string;
    size?: ComponentSize;
    tooltip?: boolean;
    tooltipPlacement?: Placement;
}>();

const emit = defineEmits<{
    (e: "click", event: PointerEvent): void;
}>();

function onClick(event: PointerEvent) {
    if (props.disabled) {
        event.preventDefault();
    } else {
        emit("click", event);
    }
}

const baseComponent = useClickableElement(props);
const currentTitle = useCurrentTitle(props);
const tooltipId = useUid("g-tooltip");

const showTooltip = computed(() => props.tooltip && currentTitle.value);

const linkRef = ref<HTMLElement | InstanceType<typeof RouterLink> | null>(null);
const linkElementRef = useResolveElement(linkRef);
</script>

<template>
    <component
        :is="baseComponent"
        ref="linkRef"
        class="g-link"
        :data-title="currentTitle"
        :to="props.to"
        :href="props.to ?? props.href"
        :title="props.tooltip ? false : currentTitle"
        :aria-describedby="showTooltip ? tooltipId : false"
        :aria-disabled="props.disabled"
        v-bind="$attrs"
        @click="onClick">
        <slot></slot>

        <!-- TODO: make tooltip a sibling in Vue 3 -->
        <GTooltip
            v-if="showTooltip"
            :id="tooltipId"
            :reference="linkElementRef"
            :text="currentTitle"
            :placement="props.tooltipPlacement" />
    </component>
</template>

<style scoped lang="scss">
.g-link {
    border: none;
    background: none;
    padding: 0;
    color: var(--color-blue-600);
    display: inline;
    line-height: unset;
    vertical-align: unset;
    user-select: text;
    font-weight: bold;

    &:hover,
    &:focus,
    &:focus-visible {
        text-decoration: underline;
    }

    &:focus-visible {
        box-shadow: 0 0 0 0.2rem var(--color-blue-400);
    }
}
</style>
