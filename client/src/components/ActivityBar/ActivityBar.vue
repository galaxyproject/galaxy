<script setup lang="ts">
import draggable from "vuedraggable";
import { ref, type Ref } from "vue";
import { storeToRefs } from "pinia";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { useActivityStore, type Activity } from "@/stores/activityStore";
import { useRoute } from "vue-router/composables";
import { convertDropData } from "@/stores/activitySetup";
import { useEventStore } from "@/stores/eventStore";
import ContextMenu from "@/components/Common/ContextMenu.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox.vue";
import WorkflowBox from "@/components/Panels/WorkflowBox.vue";
import ActivityItem from "./ActivityItem.vue";
import ActivitySettings from "./ActivitySettings.vue";
import InteractiveItem from "./Items/InteractiveItem.vue";
import UploadItem from "./Items/UploadItem.vue";
import NotificationItem from "./Items/NotificationItem.vue";

const { config } = useConfig();

const route = useRoute();
const userStore = useUserStore();
const eventStore = useEventStore();
const activityStore = useActivityStore();
const { isAnonymous } = storeToRefs(userStore);

const emit = defineEmits(["dragstart"]);

// sync built-in activities with cached activities
activityStore.sync();

// activities from store
const { activities } = storeToRefs(activityStore);

// context menu references
const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);

// drag references
const dragTarget: Ref<EventTarget | null> = ref(null);
const dragItem: Ref<Activity | null> = ref(null);

// drag state
const isDragging = ref(false);

/**
 * Checks if the route of an activitiy is currently being visited and panels are collapsed
 */
function isActiveRoute(activityTo: string) {
    return route.path === activityTo && isActiveSideBar("");
}

/**
 * Checks if a panel has been expanded
 */
function isActiveSideBar(menuKey: string) {
    return userStore.toggledSideBar === menuKey;
}

/**
 * Evaluates the drop data and keeps track of the drop area
 */
function onDragEnter(evt: MouseEvent) {
    const eventData = eventStore.getDragData();
    if (eventData) {
        dragTarget.value = evt.target;
        dragItem.value = convertDropData(eventData);
        emit("dragstart", dragItem.value);
    } else {
        dragItem.value = null;
    }
}

/**
 * Removes the dragged activity when exiting the drop area
 */
function onDragLeave(evt: MouseEvent) {
    if (dragItem.value && dragTarget.value == evt.target) {
        const dragId = dragItem.value.id;
        activities.value = activities.value.filter((a) => a.id !== dragId);
    }
}

/**
 * Insert the dragged item into the activities list
 */
function onDragOver(evt: MouseEvent) {
    const target = (evt.target as HTMLElement).closest(".activity-item");
    if (target && dragItem.value) {
        const targetId = target.id;
        const targetIndex = activities.value.findIndex((a) => `activity-${a.id}` === targetId);
        if (targetIndex !== -1) {
            const dragId: string = dragItem.value.id;
            const targetActivity = activities.value[targetIndex];
            if (targetActivity && targetActivity.id !== dragId) {
                const activitiesTemp = activities.value.filter((a) => a.id !== dragId);
                activitiesTemp.splice(targetIndex, 0, dragItem.value);
                activities.value = activitiesTemp;
            }
        }
    }
}

/**
 * Tracks the state of activities which expand or collapse the sidepanel
 */
function onToggleSidebar(toggle: string) {
    userStore.toggleSideBar(toggle);
}

/**
 * Positions and displays the context menu
 */
function toggleContextMenu(evt: MouseEvent) {
    if (evt && !contextMenuVisible.value) {
        evt.preventDefault();
        contextMenuVisible.value = true;
        contextMenuX.value = evt.x;
        contextMenuY.value = evt.y;
    } else {
        contextMenuVisible.value = false;
    }
}
</script>

<template>
    <div class="d-flex">
        <div
            class="activity-bar d-flex flex-column no-highlight"
            data-description="activity bar"
            @contextmenu="toggleContextMenu"
            @dragover.prevent="onDragOver"
            @dragenter.prevent="onDragEnter"
            @dragleave.prevent="onDragLeave">
            <b-nav vertical class="flex-nowrap p-1 h-100 vertical-overflow">
                <draggable
                    :list="activities"
                    :class="{ 'activity-popper-disabled': isDragging }"
                    :force-fallback="true"
                    chosen-class="activity-chosen-class"
                    drag-class="activity-drag-class"
                    ghost-class="activity-chosen-class"
                    @start="isDragging = true"
                    @end="isDragging = false">
                    <div v-for="(activity, activityIndex) in activities" :key="activityIndex">
                        <div v-if="activity.visible">
                            <UploadItem
                                v-if="activity.id === 'upload'"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                @click="onToggleSidebar()" />
                            <InteractiveItem
                                v-else-if="activity.id === 'interactivetools'"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :is-active="isActiveRoute(activity.to)"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :to="activity.to"
                                @click="onToggleSidebar()" />
                            <ActivityItem
                                v-else-if="['tools', 'workflows'].includes(activity.id)"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :is-active="isActiveSideBar(activity.id)"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :to="activity.to"
                                @click="onToggleSidebar(activity.id)" />
                            <ActivityItem
                                v-else-if="activity.to"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :is-active="isActiveRoute(activity.to)"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :to="activity.to"
                                @click="onToggleSidebar()" />
                        </div>
                    </div>
                </draggable>
            </b-nav>
            <b-nav vertical class="flex-nowrap p-1">
                <NotificationItem
                    v-if="!isAnonymous && config.enable_notification_system"
                    id="activity-notifications"
                    icon="bell"
                    :is-active="isActiveRoute('/user/notifications')"
                    title="Notifications"
                    to="/user/notifications"
                    @click="onToggleSidebar()" />
                <ActivityItem
                    id="activity-settings"
                    icon="cog"
                    :is-active="isActiveRoute('/user')"
                    title="Settings"
                    tooltip="Edit preferences"
                    to="/user"
                    @click="onToggleSidebar()" />
            </b-nav>
        </div>
        <FlexPanel v-if="isActiveSideBar('tools')" key="tools" side="left" :collapsible="false">
            <ToolBox />
        </FlexPanel>
        <FlexPanel v-else-if="isActiveSideBar('workflows')" key="workflows" side="left" :collapsible="false">
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
