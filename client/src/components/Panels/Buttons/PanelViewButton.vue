<template>
    <b-dropdown
        no-caret
        right
        role="button"
        title="Panel Views"
        variant="link"
        aria-label="View all tool panel configurations"
        class="tool-panel-dropdown float-right"
        toggle-class = "panel-header-button-toolbox float-right"
        size="sm"
        v-b-tooltip.hover>
        <template v-slot:button-content>
            <span class="fa fa-list" />
            <!-- Maybe cog? -->
        </template>
        <PanelViewMenuItem
            :current-panel-view="currentPanelView"
            :panel-view="defaultPanelView"
            @onSelect="updatePanelView" />
        <b-dropdown-divider></b-dropdown-divider>
        <b-dropdown-group v-for="group in groupedPanelViews" :key="group.type" :id="group.type" :header="group.title">
            <PanelViewMenuItem
                v-for="(panelView, key) in group.panelViews"
                :key="key"
                :current-panel-view="currentPanelView"
                :panel-view="panelView"
                @onSelect="updatePanelView" />
        </b-dropdown-group>
        <b-dropdown-divider v-if="groupedPanelViews.length > 0"></b-dropdown-divider>
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
    { type: "ontology", title: "... by Ontology" },
    { type: "activity", title: "... for Activity" },
    { type: "publication", title: "... from Publication" },
    { type: "training", title: "... for Training" },
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
