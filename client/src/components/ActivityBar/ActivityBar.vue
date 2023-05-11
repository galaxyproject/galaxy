<script setup>
import { useUserStore } from "@/stores/userStore";
import UploadItem from "./Items/UploadItem.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import ActivityItem from "./ActivityItem";

const userStore = useUserStore();

function sidebarIsActive(menuKey) {
    return userStore.toggledSideBar === menuKey;
}

function onToggleSidebar(toggle) {
    userStore.toggleSideBar(toggle);
}
</script>
<template>
    <div class="d-flex">
        <div class="activity-bar d-flex flex-column">
            <b-nav vertical class="flex-nowrap p-1 h-100 vertical-overflow">
                <upload-item />
                <ActivityItem
                    id="activity-tools"
                    icon="wrench"
                    title="Tools"
                    tooltip="Search and run tools"
                    :is-active="sidebarIsActive('search')"
                    @click="onToggleSidebar('search')" />
                <ActivityItem
                    id="activity-workflow"
                    title="Workflow"
                    icon="sitemap"
                    tooltip="Chain tools into workflows"
                    to="/workflows/list" />
                <ActivityItem
                    id="activity-visualization"
                    icon="chart-bar"
                    title="Visualize"
                    tooltip="Visualize datasets"
                    to="/visualizations" />
            </b-nav>
            <b-nav vertical class="flex-nowrap p-1">
                <ActivityItem
                    id="activity-settings"
                    icon="cog"
                    title="Settings"
                    tooltip="Edit preferences"
                    to="/user" />
            </b-nav>
        </div>
        <FlexPanel v-if="sidebarIsActive('search')" key="search" side="left" :collapsible="false">
            <ToolBox />
        </FlexPanel>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.activity-bar {
    background: $panel-bg-color;
    width: 4rem;
}

.activity-bar::-webkit-scrollbar {
    display: none;
}

.panels-enter-active,
.panels-leave-active {
    transition: all 0.3s;
}

.panels-enter,
.panels-leave-to {
    transform: translateX(-100%);
}

.vertical-overflow {
    overflow-y: auto;
    overflow-x: hidden;
}
</style>
