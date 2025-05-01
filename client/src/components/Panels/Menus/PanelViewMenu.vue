<template>
    <b-button
        v-if="showAdvanced"
        variant="link"
        class="w-100 text-decoration-none"
        size="sm"
        @click="$emit('update:show-advanced', !showAdvanced)">
        <slot name="panel-view-selector"></slot><span class="sr-only">关闭高级工具搜索菜单</span>
    </b-button>
    <b-dropdown
        v-else
        v-b-tooltip.hover.top.noninteractive
        right
        block
        no-caret
        :disabled="storeLoading"
        :title="!storeLoading ? '显示面板选项' : '加载面板视图中'"
        variant="link"
        toggle-class="text-decoration-none"
        role="menu"
        aria-label="查看所有工具面板配置"
        class="tool-panel-dropdown w-100"
        size="sm">
        <template v-slot:button-content>
            <slot name="panel-view-selector"></slot><span class="sr-only">查看所有工具面板配置</span>
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
    { type: "ontology", title: "...按本体论分类" },
    { type: "activity", title: "...按活动分类" },
    { type: "publication", title: "...来自出版物" },
    { type: "training", title: "...用于培训" },
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
