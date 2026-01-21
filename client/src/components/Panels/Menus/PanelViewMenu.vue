<script setup lang="ts">
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownDivider, BDropdownGroup } from "bootstrap-vue";
import type { IconDefinition } from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { type Panel, useToolStore } from "@/stores/toolStore";
import localize from "@/utils/localization";

import { MY_PANEL_VIEW_ID, MY_PANEL_VIEW_NAME } from "../panelViews";
import { types_to_icons } from "../utilities";

import PanelViewMenuItem from "./PanelViewMenuItem.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const groupsDefinitions = [
    { type: "ontology", title: "...by Ontology" },
    { type: "activity", title: "...for Activity" },
    { type: "publication", title: "...from Publication" },
    { type: "training", title: "...for Training" },
];
const groupedPanelViewTypes = new Set(groupsDefinitions.map((group) => group.type));

const props = defineProps<{
    /** Whether the menu is compact: doesn't take up full width of the parent when `true`.
     * @default false
     */
    compact?: boolean;
}>();

const toolStore = useToolStore();
const { currentPanelView, loading, panels } = storeToRefs(toolStore);

const panelName = ref("");

const defaultPanelView = computed(() => panels.value["default"] || Object.values(panels.value)[0]);
const currentPanel = computed(() => panels.value[currentPanelView.value]);
const isFavoritesView = computed(() => currentPanel.value?.view_type === "favorites");
const isMyToolsView = computed(() => currentPanelView.value === MY_PANEL_VIEW_ID);

const panelIcon = computed<IconDefinition | null>(() => {
    if (
        currentPanelView.value !== "default" &&
        panels.value &&
        typeof panels.value[currentPanelView.value]?.view_type === "string"
    ) {
        const viewType = panels.value[currentPanelView.value]?.view_type;
        return viewType && types_to_icons[viewType] ? types_to_icons[viewType] : null;
    } else {
        return null;
    }
});

const styleClasses = computed(() => {
    return {
        "w-100": !props.compact,
    };
});

const toolPanelHeader = computed(() => {
    if (loading.value && panelName.value) {
        return localize(panelName.value);
    } else if (currentPanelView.value !== "default" && panels.value && currentPanel.value?.name) {
        const name = currentPanel.value.id === MY_PANEL_VIEW_ID ? MY_PANEL_VIEW_NAME : currentPanel.value.name;
        return localize(name);
    } else {
        return localize("Tools");
    }
});

const headingClass = computed(() =>
    currentPanelView.value !== "default" && !isMyToolsView.value ? "font-italic" : "",
);
const showPanelIcon = computed(() => !!panelIcon.value && !loading.value && !isMyToolsView.value);

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

const ungroupedPanelViews = computed(() => {
    const defaultPanelId = defaultPanelView.value?.id;
    return Object.values(panels.value).filter((panel) => {
        if (!panel || panel.id === defaultPanelId) {
            return false;
        }
        const viewType = panel.view_type;
        return viewType ? !groupedPanelViewTypes.has(viewType) : false;
    });
});

function panelViewsOfType(panelViewType: string) {
    const panelViews = [];
    for (const panelViewId in panels.value) {
        const panelView = panels.value[panelViewId];
        if (panelView?.view_type === panelViewType) {
            panelViews.push(panelView);
        }
    }
    return panelViews;
}

async function updatePanelView(panel: Panel) {
    panelName.value = panel.id === MY_PANEL_VIEW_ID ? MY_PANEL_VIEW_NAME : panel.name || "";
    await toolStore.setPanel(panel.id);
    panelName.value = "";
}
</script>

<template>
    <BDropdown
        v-b-tooltip.hover.top.noninteractive
        right
        block
        no-caret
        :disabled="loading"
        :title="!loading ? localize('Show panel options') : 'Loading panel view'"
        variant="link"
        toggle-class="text-decoration-none"
        role="menu"
        aria-label="View all tool panel configurations"
        class="tool-panel-dropdown"
        :class="styleClasses"
        size="sm">
        <template v-slot:button-content>
            <span class="sr-only">View all tool panel configurations</span>
            <div class="d-flex panel-view-selector justify-content-between flex-gapx-1">
                <div>
                    <FontAwesomeIcon
                        v-if="showPanelIcon && !isFavoritesView"
                        class="mr-1"
                        :icon="panelIcon"
                        data-description="panel view header icon" />
                    <Heading id="toolbox-heading" :class="headingClass" h2 inline size="sm">
                        <span v-if="loading && panelName">
                            <LoadingSpan :message="toolPanelHeader" />
                        </span>
                        <span v-else>{{ toolPanelHeader }}</span>
                    </Heading>
                    <FontAwesomeIcon
                        v-if="showPanelIcon && isFavoritesView"
                        class="ml-1"
                        :icon="panelIcon"
                        data-description="panel view header icon" />
                </div>
                <div class="panel-header-buttons">
                    <FontAwesomeIcon :icon="faCaretDown" />
                </div>
            </div>
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

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.panel-view-selector {
    color: $panel-header-text-color;
}

.tool-panel-dropdown {
    :deep(.dropdown-menu) {
        overflow: auto;
        max-height: 50vh;
        min-width: 100%;
    }
}
</style>
