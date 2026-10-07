<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, ref, useSlots, watch } from "vue";

import type { TabRegistration, TabsContext } from "./GTabs.vue";

const props = withDefaults(
    defineProps<{
        title?: string;
        titleLinkClass?: string | string[];
        titleItemClass?: string | string[];
        titleLinkAttributes?: Record<string, string>;
        buttonId?: string;
        id?: string;
        active?: boolean;
        disabled?: boolean;
        lazy?: boolean;
    }>(),
    {
        title: undefined,
        titleLinkClass: undefined,
        titleItemClass: undefined,
        titleLinkAttributes: undefined,
        buttonId: undefined,
        id: undefined,
        active: false,
        disabled: false,
        lazy: undefined,
    },
);

const emit = defineEmits<{
    (e: "click"): void;
}>();

const slots = useSlots();
const context = inject<TabsContext>("g-tabs-context")!;
const tabIndex = ref(-1);
const hasBeenActive = ref(false);

const isActive = computed(() => context.activeIndex.value === tabIndex.value);

watch(isActive, (active) => {
    if (active) {
        hasBeenActive.value = true;
        emit("click");
    }
});

const shouldRender = computed(() => {
    const isLazy = props.lazy !== undefined ? props.lazy : context.tabsLazy;
    if (!isLazy) {
        return true;
    }
    return hasBeenActive.value;
});

function buildRegistration(): TabRegistration {
    return {
        title: props.title,
        titleRenderer: slots.title ? () => slots.title!() : undefined,
        disabled: props.disabled,
        id: props.id,
        buttonId: props.buttonId,
        titleLinkClass: props.titleLinkClass,
        titleItemClass: props.titleItemClass,
        titleLinkAttributes: props.titleLinkAttributes,
        active: props.active,
        lazy: props.lazy,
    };
}

onMounted(() => {
    tabIndex.value = context.registerTab(buildRegistration());
    if (props.active || isActive.value) {
        hasBeenActive.value = true;
    }
});

watch(
    () => [
        props.title,
        props.disabled,
        props.titleLinkClass,
        props.titleItemClass,
        props.titleLinkAttributes,
        props.buttonId,
    ],
    () => {
        if (tabIndex.value >= 0) {
            context.updateTab(tabIndex.value, buildRegistration());
        }
    },
);

onBeforeUnmount(() => {
    if (tabIndex.value >= 0) {
        context.unregisterTab(tabIndex.value);
    }
});
</script>

<template>
    <div
        v-if="shouldRender"
        v-show="isActive"
        :id="id"
        class="tab-pane"
        :class="{ active: isActive, show: isActive, 'card-body': context.tabsCard }"
        role="tabpanel">
        <slot />
    </div>
</template>
