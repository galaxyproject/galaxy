<script setup lang="ts">
import { BDropdown, BDropdownDivider, BDropdownGroup } from "bootstrap-vue";
import { computed } from "vue";

import type { Panel } from "@/stores/toolStore";

import PanelViewMenuItem from "./PanelViewMenuItem.vue";

const groupsDefinitions = [
    { type: "ontology", title: "...by Ontology" },
    { type: "activity", title: "...for Activity" },
    { type: "publication", title: "...from Publication" },
    { type: "training", title: "...for Training" },
];

const props = defineProps<{
    panelViews: Record<string, Panel>;
    currentPanelView: string;
    storeLoading: boolean;
}>();

const emit = defineEmits<{
    (e: "updatePanelView", panelViewId: string): void;
}>();

const defaultPanelView = computed(() => props.panelViews["default"] || Object.values(props.panelViews)[0]);

const groupedPanelViews = computed(() => {
    const groups = [];
    for (const group of groupsDefinitions) {
        const viewType = group.type;
        const panelViews = panelViewsOfType(viewType);
        if (panelViews.length > 0) {
            groups.push({
                type: viewType,
                title: group.title,
                panelViews: panelViews,
            });
        }
    }
    return groups;
});

const ungroupedPanelViews = computed(() => panelViewsOfType("generic"));

function panelViewsOfType(panelViewType: string) {
    const panelViews = [];
    for (const panelViewId in props.panelViews) {
        const panelView = props.panelViews[panelViewId];
        if (panelView?.view_type === panelViewType) {
            panelViews.push(panelView);
        }
    }
    return panelViews;
}

function updatePanelView(panelView: Panel) {
    emit("updatePanelView", panelView.id);
}
</script>

<template>
    <BDropdown
        v-b-tooltip.hover.top.noninteractive
        right
        block
        no-caret
        :disabled="storeLoading"
        :title="!storeLoading ? 'Show panel options' : 'Loading panel view'"
        variant="link"
        toggle-class="text-decoration-none"
        role="menu"
        aria-label="View all tool panel configurations"
        class="tool-panel-dropdown w-100"
        size="sm">
        <template v-slot:button-content>
            <slot name="panel-view-selector"></slot><span class="sr-only">View all tool panel configurations</span>
        </template>
        <PanelViewMenuItem
            v-if="defaultPanelView"
            :current-panel-view="currentPanelView"
            :panel-view="defaultPanelView"
            @onSelect="updatePanelView" />
        <BDropdownGroup v-for="group in groupedPanelViews" :id="group.type" :key="group.type">
            <template v-slot:header>
                <small class="font-weight-bold">{{ group.title }}</small>
            </template>
            <PanelViewMenuItem
                v-for="(panelView, key) in group.panelViews"
                :key="key"
                :current-panel-view="currentPanelView"
                :panel-view="panelView"
                @onSelect="updatePanelView" />
        </BDropdownGroup>
        <BDropdownDivider v-if="ungroupedPanelViews.length > 0" />
        <PanelViewMenuItem
            v-for="(panelView, key) in ungroupedPanelViews"
            :key="key"
            :current-panel-view="currentPanelView"
            :panel-view="panelView"
            @onSelect="updatePanelView" />
    </BDropdown>
</template>

<style lang="scss">
.tool-panel-dropdown .dropdown-menu {
    overflow: auto;
    max-height: 50vh;
    min-width: 100%;
}
</style>
