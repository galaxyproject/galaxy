<script setup>
import { getGalaxyInstance } from "app";
import { useUserStore } from "@/stores/userStore";
import { WindowManager } from "@/layout/window-manager";
import { useRoute, useRouter } from "vue-router/composables";
import { computed, ref } from "vue";
import UploadItem from "./Items/UploadItem.vue";
import WorkflowItem from "./Items/WorkflowItem.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox.vue";
import ActivityItem from "./ActivityItem";

const route = useRoute();
const router = useRouter();
const showCenter = ref(false);
const userStore = useUserStore();

const workflows = computed(() => {
    const Galaxy = getGalaxyInstance();
    return Galaxy.config.stored_workflow_menu_entries;
});

function sidebarIsActive(menuKey) {
    return userStore.toggledSideBar === menuKey;
}

function onToggleSidebar(toggle) {
    userStore.toggleSideBar(toggle);
}

function showVisualizationList() {
    router.push("/visualizations");
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
                <workflow-item :workflows="workflows" />
                <ActivityItem
                    id="activity-visualization"
                    icon="chart-bar"
                    title="Visualize"
                    tooltip="Visualize datasets"
                    @click="showVisualizationList" />
            </b-nav>
            <b-nav vertical class="flex-nowrap p-1">
                <ActivityItem
                    id="activity-settings"
                    icon="cog"
                    title="Configure"
                    tooltip="Configure the Activity Bar" />
            </b-nav>
        </div>
        <div v-show="sidebarIsActive('search')" key="search">
            <ToolBox class="left-column" />
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.left-column {
    width: 15rem;
}

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
