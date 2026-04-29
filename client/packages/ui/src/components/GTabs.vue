<script setup lang="ts">
import type { PropType, Ref, VNode } from "vue";
import { computed, defineComponent, h, provide, ref, watch } from "vue";

export interface TabRegistration {
    title?: string;
    titleRenderer?: () => VNode[] | undefined;
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
    tabsCard: boolean;
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
    tabsCard: props.card,
});

const navClasses = computed(() => ({
    "nav-tabs": !props.pills,
    "nav-pills": props.pills,
    "nav-justified": props.justified,
    "nav-fill": props.fill,
    "card-header-tabs": props.card && !props.pills && !props.vertical,
    "card-header-pills": props.card && props.pills && !props.vertical,
    "flex-column": props.vertical,
    "card-header": props.card && props.vertical,
    "h-100": props.card && props.vertical,
    "border-bottom-0": props.card && props.vertical,
    "rounded-0": props.card && props.vertical,
}));

// "tabs" class matches BTabs' outer div class for Selenium selector compatibility
const containerClasses = computed(() => ({
    tabs: true,
    row: props.vertical,
    "no-gutters": props.vertical && props.card,
}));

// Vue 2.7 doesn't support plain functions as components via <component :is>,
// so we define a proper component with setup returning a render function.
const TabTitleContent = defineComponent({
    props: {
        tab: {
            type: Object as PropType<TabRegistration>,
            required: true,
        },
    },
    setup(props) {
        return () => {
            const nodes = props.tab.titleRenderer?.();
            if (nodes && nodes.length > 0) {
                return nodes.length === 1 ? nodes[0] : h("span", nodes);
            }
            return props.tab.title || "";
        };
    },
});
</script>

<template>
    <div :class="containerClasses">
        <!--
            Nav items are duplicated across the v-if/v-else branches because vertical mode needs
            a col-auto wrapper div for Bootstrap's grid layout. Keep both branches in sync.

            TODO: migrate <a> to <button> in both branches — semantically more correct for tabs.
            Using <a href="#"> for now because Selenium selectors in navigation.yml target `a.nav-link`
            (e.g. `.nav-item[title="..."] > a.nav-link`) matching what BTabs rendered.
            When updating, also change those selectors to drop the element type requirement.
        -->

        <!-- Vertical: BSV wraps the nav in a col-auto div for Bootstrap grid layout -->
        <div v-if="props.vertical" class="col-auto">
            <ul class="nav" :class="navClasses" role="tablist">
                <li
                    v-for="(tab, index) in tabs"
                    :key="index"
                    class="nav-item"
                    :class="tab.titleItemClass"
                    :title="tab.title"
                    role="presentation">
                    <a
                        :id="tab.buttonId"
                        class="nav-link"
                        :class="[tab.titleLinkClass, { active: index === activeIndex, disabled: tab.disabled }]"
                        role="tab"
                        href="#"
                        :aria-selected="index === activeIndex"
                        :aria-controls="tab.id"
                        :aria-disabled="tab.disabled"
                        :data-tab-title="tab.title"
                        v-bind="tab.titleLinkAttributes"
                        @click.prevent="!tab.disabled && setActive(index)">
                        <TabTitleContent v-if="tab.titleRenderer" :tab="tab" />
                        <template v-else>{{ tab.title }}</template>
                    </a>
                </li>
            </ul>
        </div>

        <!-- Non-vertical: nav is a direct child -->
        <ul v-else class="nav" :class="navClasses" role="tablist">
            <li
                v-for="(tab, index) in tabs"
                :key="index"
                class="nav-item"
                :class="tab.titleItemClass"
                :title="tab.title"
                role="presentation">
                <a
                    :id="tab.buttonId"
                    class="nav-link"
                    :class="[tab.titleLinkClass, { active: index === activeIndex, disabled: tab.disabled }]"
                    role="tab"
                    href="#"
                    :aria-selected="index === activeIndex"
                    :aria-controls="tab.id"
                    :aria-disabled="tab.disabled"
                    :data-tab-title="tab.title"
                    v-bind="tab.titleLinkAttributes"
                    @click.prevent="!tab.disabled && setActive(index)">
                    <TabTitleContent v-if="tab.titleRenderer" :tab="tab" />
                    <template v-else>{{ tab.title }}</template>
                </a>
            </li>
        </ul>

        <div class="tab-content" :class="{ col: props.vertical }">
            <slot />
        </div>
    </div>
</template>
