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

// TODO: get state from store
const activities = ref(Activities.slice());
const isDragging = ref(false);

function sidebarIsActive(menuKey) {
    return userStore.toggledSideBar === menuKey;
}

function onToggleSidebar(toggle) {
    userStore.toggleSideBar(toggle);
}

function onChange() {
    // TODO: push state to store
    const newOrder = activities.value.map((a) => a.id);
    console.log(newOrder);
}
</script>

<template>
    <div class="d-flex">
        <div class="activity-bar d-flex flex-column no-highlight">
            <b-nav vertical class="flex-nowrap p-1 h-100 vertical-overflow">
                <draggable
                    :list="activities"
                    :class="{ 'activity-popper-disabled': isDragging }"
                    :force-fallback="true"
                    chosen-class="activity-chosen-class"
                    drag-class="activity-drag-class"
                    ghost-class="activity-chosen-class"
                    @change="onChange"
                    @start="isDragging = true"
                    @end="isDragging = false">
                    <div v-for="activity in activities">
                        <upload-item v-if="activity.id === 'upload'" />
                        <ActivityItem
                            v-if="activity.id === 'tools'"
                            id="activity-tools"
                            icon="wrench"
                            title="Tools"
                            tooltip="Search and run tools"
                            :is-active="sidebarIsActive('search')"
                            @click="onToggleSidebar('search')" />
                        <ActivityItem
                            v-if="activity.id === 'workflow'"
                            id="activity-workflow"
                            title="Workflow"
                            icon="sitemap"
                            tooltip="Chain tools into workflows"
                            to="/workflows/list" />
                        <ActivityItem
                            v-if="activity.to"
                            :key="activity.id"
                            :id="`activity-${activity.id}`"
                            :title="activity.title"
                            :icon="activity.icon"
                            :tooltip="activity.tooltip"
                            :to="activity.to" />
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

<style lang="scss">
@import "theme/blue.scss";

.activity-bar {
    background: $panel-bg-color;
}

.activity-bar::-webkit-scrollbar {
    display: none;
}

.activity-chosen-class {
    background: $brand-toggle;
    border-radius: $border-radius-extralarge;
}

.activity-drag-class {
    display: none;
}

.activity-popper-disabled {
    .popper-element {
        display: none;
    }
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
