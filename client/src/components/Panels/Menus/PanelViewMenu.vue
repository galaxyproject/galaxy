<template>
    <b-button
        v-if="showAdvanced"
        variant="link"
        class="w-100 text-decoration-none"
        size="sm"
        @click="$emit('update:show-advanced', !showAdvanced)">
        <slot name="panel-view-selector"></slot><span class="sr-only">Close advanced tool search menu</span>
    </b-button>
    <b-dropdown
        v-else
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
            :current-panel-view="currentPanelView"
            :panel-view="defaultPanelView"
            @onSelect="updatePanelView" />
        <b-dropdown-group v-for="group in groupedPanelViews" :id="group.type" :key="group.type">
            <template v-slot:header>
                <small class="font-weight-bold">{{ group.title }}</small>
            </template>
            <PanelViewMenuItem
                v-for="(panelView, key) in group.panelViews"
                :key="key"
                :current-panel-view="currentPanelView"
                :panel-view="panelView"
                @onSelect="updatePanelView" />
        </b-dropdown-group>
        <b-dropdown-divider v-if="ungroupedPanelViews.length > 0" />
        <PanelViewMenuItem
            v-for="(panelView, key) in ungroupedPanelViews"
            :key="key"
            :current-panel-view="currentPanelView"
            :panel-view="panelView"
            @onSelect="updatePanelView" />
    </b-dropdown>
</template>

<script>
import PanelViewMenuItem from "./PanelViewMenuItem";

const groupsDefinitions = [
    { type: "ontology", title: "...by Ontology" },
    { type: "activity", title: "...for Activity" },
    { type: "publication", title: "...from Publication" },
    { type: "training", title: "...for Training" },
];

export default {
    components: { PanelViewMenuItem },
    props: {
        panelViews: {
            type: Object,
        },
        currentPanelView: {
            type: String,
        },
        showAdvanced: {
            type: Boolean,
            default: false,
        },
        storeLoading: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        defaultPanelView() {
            return this.panelViewsOfType("default")[0];
        },
        groupedPanelViews() {
            const groups = [];
            for (const group of groupsDefinitions) {
                const viewType = group.type;
                const panelViews = this.panelViewsOfType(viewType);
                if (panelViews.length > 0) {
                    groups.push({
                        type: viewType,
                        title: group.title,
                        panelViews: panelViews,
                    });
                }
            }
            return groups;
        },
        ungroupedPanelViews() {
            return this.panelViewsOfType("generic");
        },
    },
    methods: {
        updatePanelView(panelView) {
            this.$emit("updatePanelView", panelView.id);
        },
        panelViewsOfType(panelViewType) {
            const panelViews = [];
            for (const panelViewId in this.panelViews) {
                const panelView = this.panelViews[panelViewId];
                if (panelView.view_type == panelViewType) {
                    panelViews.push(panelView);
                }
            }
            return panelViews;
        },
    },
};
</script>

<style lang="scss">
.tool-panel-dropdown .dropdown-menu {
    overflow: auto;
    max-height: 50vh;
    min-width: 100%;
}
</style>
