<script setup lang="ts">
import type { Ref, VNode } from "vue";
import { computed, h, provide, ref, watch } from "vue";

export interface TabRegistration {
    title?: string;
    titleRenderer?: () => VNode[];
    disabled?: boolean;
    id?: string;
    buttonId?: string;
    titleLinkClass?: string | string[];
    titleItemClass?: string | string[];
    titleLinkAttributes?: Record<string, string>;
    active?: boolean;
    lazy?: boolean;
}

export interface TabsContext {
    activeIndex: Ref<number>;
    registerTab: (tab: TabRegistration) => number;
    unregisterTab: (index: number) => void;
    updateTab: (index: number, tab: TabRegistration) => void;
    setActive: (index: number) => void;
    tabsLazy: boolean;
}

const props = withDefaults(
    defineProps<{
        value?: number;
        justified?: boolean;
        fill?: boolean;
        pills?: boolean;
        card?: boolean;
        vertical?: boolean;
        lazy?: boolean;
    }>(),
    {
        value: undefined,
        justified: false,
        fill: false,
        pills: false,
        card: false,
        vertical: false,
        lazy: false,
    },
);

const emit = defineEmits<{
    (e: "input", index: number): void;
}>();

const internalActive = ref(0);

const activeIndex = computed({
    get: () => (props.value !== undefined ? props.value : internalActive.value),
    set: (val: number) => {
        internalActive.value = val;
        emit("input", val);
    },
});

const tabs = ref<TabRegistration[]>([]);

function registerTab(tab: TabRegistration): number {
    const index = tabs.value.length;
    tabs.value.push(tab);
    if (tab.active && index !== activeIndex.value) {
        activeIndex.value = index;
    }
    return index;
}

function unregisterTab(index: number) {
    tabs.value.splice(index, 1);
    if (activeIndex.value >= tabs.value.length && tabs.value.length > 0) {
        activeIndex.value = tabs.value.length - 1;
    }
}

function updateTab(index: number, tab: TabRegistration) {
    if (index >= 0 && index < tabs.value.length) {
        tabs.value[index] = tab;
    }
}

function setActive(index: number) {
    if (index >= 0 && index < tabs.value.length && !tabs.value[index]?.disabled) {
        activeIndex.value = index;
    }
}

watch(
    () => props.value,
    (val) => {
        if (val !== undefined) {
            internalActive.value = val;
        }
    },
);

provide<TabsContext>("g-tabs-context", {
    activeIndex,
    registerTab,
    unregisterTab,
    updateTab,
    setActive,
    tabsLazy: props.lazy,
});

const navClasses = computed(() => ({
    "nav-tabs": !props.pills,
    "nav-pills": props.pills,
    "nav-justified": props.justified,
    "nav-fill": props.fill,
    "card-header-tabs": props.card && !props.pills,
    "card-header-pills": props.card && props.pills,
    "flex-column": props.vertical,
}));

const containerClasses = computed(() => ({
    "d-flex": props.vertical,
}));

function renderTabTitle(tab: TabRegistration) {
    if (tab.titleRenderer) {
        return tab.titleRenderer();
    }
    return [h("span", tab.title)];
}
</script>

<template>
    <div :class="containerClasses">
        <ul class="nav" :class="navClasses" role="tablist">
            <li
                v-for="(tab, index) in tabs"
                :key="index"
                class="nav-item"
                :class="tab.titleItemClass"
                role="presentation">
                <button
                    :id="tab.buttonId"
                    class="nav-link"
                    :class="[tab.titleLinkClass, { active: index === activeIndex, disabled: tab.disabled }]"
                    role="tab"
                    type="button"
                    :aria-selected="index === activeIndex"
                    :disabled="tab.disabled"
                    v-bind="tab.titleLinkAttributes"
                    @click="setActive(index)">
                    <component :is="() => renderTabTitle(tab)" />
                </button>
            </li>
        </ul>
        <div class="tab-content" :class="{ 'flex-grow-1': props.vertical }">
            <slot />
        </div>
    </div>
</template>
