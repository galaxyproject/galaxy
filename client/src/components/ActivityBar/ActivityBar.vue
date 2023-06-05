<script setup>
import draggable from "vuedraggable";
import { ref } from "vue";
import { useUserStore } from "@/stores/userStore";
import { useActivityStore } from "@/stores/activityStore";
import { useEventStore } from "@/stores/eventStore";
import ContextMenu from "@/components/Common/ContextMenu.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox.vue";
import ActivityItem from "./ActivityItem.vue";
import ActivitySettings from "./ActivitySettings.vue";
import { convertDropData } from "./activities.js";
import UploadItem from "./Items/UploadItem.vue";
import WorkflowBox from "@/components/Panels/WorkflowBox.vue";

const activityStore = useActivityStore();
const eventStore = useEventStore();
const userStore = useUserStore();

// activities from store
const activities = ref(activityStore.getAll());

// context menu references
const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);

// drag references
const dragTarget = ref(null);
const dragItem = ref(null);

// drag state
const isDragging = ref(false);

function sidebarIsActive(menuKey) {
    return userStore.toggledSideBar === menuKey;
}

function onToggleSidebar(toggle) {
    userStore.toggleSideBar(toggle);
}

function onChange() {
    activityStore.saveAll(activities);
}

function toggleContextMenu(evt) {
    if (evt && !contextMenuVisible.value) {
        evt.preventDefault();
        contextMenuVisible.value = true;
        contextMenuX.value = evt.x;
        contextMenuY.value = evt.y;
    } else {
        contextMenuVisible.value = false;
    }
}

function onDragOver(evt) {
    const target = evt.target.closest(".activity-item");
    if (target && dragItem.value) {
        const targetId = target.id;
        const targetIndex = activities.value.findIndex((a) => `activity-${a.id}` === targetId);
        if (targetIndex !== -1) {
            const dragId = dragItem.value.id;
            if (activities.value[targetIndex].id !== dragId) {
                const activitiesTemp = activities.value.filter((a) => a.id !== dragId);
                activitiesTemp.splice(targetIndex, 0, dragItem.value);
                activities.value = activitiesTemp;
            }
        }
    }
}

function onDragEnter(evt) {
    dragTarget.value = evt.target;
    dragItem.value = convertDropData(eventStore.getDragEvent());
}

function onDragLeave(evt) {
    if (dragTarget.value == evt.target) {
        const dragId = dragItem.value.id;
        const activitiesTemp = activities.value.filter((a) => a.id !== dragId);
        activities.value = activitiesTemp;
    }
}

function onDrop(evt) {
    let data;
    try {
        data = JSON.parse(evt.dataTransfer.getData("text"))[0];
    } catch (error) {
        // this was not a valid object for this dropzone, ignore
    }
}
</script>

<template>
    <div
        class="d-flex"
        @contextmenu="toggleContextMenu"
        @dragover.prevent="onDragOver"
        @dragenter.prevent="onDragEnter"
        @dragleave.prevent="onDragLeave">
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
                    <div v-for="(activity, activityIndex) in activities" :key="activityIndex">
                        <div v-if="activity.visible">
                            <upload-item
                                v-if="activity.id === 'upload'"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :title="activity.title"
                                :tooltip="activity.tooltip" />
                            <ActivityItem
                                v-if="activity.id === 'tools'"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :is-active="sidebarIsActive('tools')"
                                @click="onToggleSidebar('tools')" />
                            <ActivityItem
                                v-if="activity.id === 'workflows'"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :is-active="sidebarIsActive('workflows')"
                                @click="onToggleSidebar('workflows')" />
                            <ActivityItem
                                v-if="activity.to"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :title="activity.title"
                                :icon="activity.icon"
                                :tooltip="activity.tooltip"
                                :to="activity.to" />
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
        <FlexPanel v-if="sidebarIsActive('tools')" key="tools" side="left" :collapsible="false">
            <ToolBox />
        </FlexPanel>
        <FlexPanel v-else-if="sidebarIsActive('workflows')" key="workflows" side="left" :collapsible="false">
            <WorkflowBox />
        </FlexPanel>
        <ContextMenu :visible="contextMenuVisible" :x="contextMenuX" :y="contextMenuY" @hide="toggleContextMenu">
            <ActivitySettings />
        </ContextMenu>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";

.activity-bar {
    background: $panel-bg-color;
    border-right: $border-default;
}

.activity-bar::-webkit-scrollbar {
    display: none;
}

.activity-chosen-class {
    background: $brand-secondary;
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
