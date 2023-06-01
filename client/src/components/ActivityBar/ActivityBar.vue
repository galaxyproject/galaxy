<script setup>
import { computed, ref, watch } from "vue";
import { useUserStore } from "@/stores/userStore";
import UploadItem from "./Items/UploadItem.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import ActivityItem from "./ActivityItem.vue";
import Activities from "./activities.js";
import draggable from "vuedraggable";

const userStore = useUserStore();
const activityOrder = ref(Activities.slice());
const isDragging = ref(false);

function sidebarIsActive(menuKey) {
    return userStore.toggledSideBar === menuKey;
}

function onToggleSidebar(toggle) {
    userStore.toggleSideBar(toggle);
}
watch(activityOrder, () => {
    console.log(activityOrder);
});
function disableDragging(options) {
    console.log(options);
    return {};
}
</script>
<template>
    <div :class="{ 'd-flex': true, 'popper-disabled': isDragging }">
        <div class="activity-bar d-flex flex-column no-highlight">
            <b-nav vertical class="flex-nowrap p-1 h-100 vertical-overflow">
                <draggable
                    :list="activityOrder"
                    @start="isDragging = true"
                    @end="isDragging = false"
                    chosenClass="chosen-class"
                    dragClass="drag-class"
                    ghostClass="chosen-class">
                    <div v-for="activity in activityOrder">
                        <div>
                            <upload-item v-if="activity.id === 'upload'" />
                            <ActivityItem
                                v-if="activity.id === 'tools'"
                                id="activity-tools"
                                icon="wrench"
                                title="Tools"
                                tooltip="Search and run tools"
                                :is-active="sidebarIsActive('search')"
                                :is-dragging="isDragging"
                                @click="onToggleSidebar('search')" />
                            <ActivityItem
                                v-if="activity.id === 'workflow'"
                                id="activity-workflow"
                                title="Workflow"
                                icon="sitemap"
                                tooltip="Chain tools into workflows"
                                to="/workflows/list"
                                :is-dragging="isDragging" />
                            <ActivityItem
                                v-if="activity.to"
                                :key="activity.id"
                                :id="`activity-${activity.id}`"
                                :title="activity.title"
                                :icon="activity.icon"
                                :tooltip="activity.tooltip"
                                :to="activity.to"
                                :is-dragging="isDragging" />
                        </div>
                    </div>
                </draggable>
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

.chosen-class {
    background: $brand-toggle;
    border-radius: $border-radius-extralarge;
}

.drag-class {
    opacity: 0;
}
</style>
