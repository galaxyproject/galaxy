<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, type Ref, ref, watch } from "vue";
import { useRoute } from "vue-router/composables";
import draggable from "vuedraggable";

import { useConfig } from "@/composables/config";
import { useHashedUserId } from "@/composables/hashedUserId";
import { convertDropData } from "@/stores/activitySetup";
import { type Activity, useActivityStore } from "@/stores/activityStore";
import { useEventStore } from "@/stores/eventStore";
import { useUserStore } from "@/stores/userStore";

import InvocationsPanel from "../Panels/InvocationsPanel.vue";
import VisualizationPanel from "../Panels/VisualizationPanel.vue";
import ActivityItem from "./ActivityItem.vue";
import InteractiveItem from "./Items/InteractiveItem.vue";
import NotificationItem from "./Items/NotificationItem.vue";
import UploadItem from "./Items/UploadItem.vue";
import AdminPanel from "@/components/admin/AdminPanel.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import MultiviewPanel from "@/components/Panels/MultiviewPanel.vue";
import NotificationsPanel from "@/components/Panels/NotificationsPanel.vue";
import SettingsPanel from "@/components/Panels/SettingsPanel.vue";
import ToolPanel from "@/components/Panels/ToolPanel.vue";

// require user to long click before dragging
const DRAG_DELAY = 50;

const { config, isConfigLoaded } = useConfig();

const route = useRoute();
const userStore = useUserStore();

const { hashedUserId } = useHashedUserId();

const eventStore = useEventStore();
const activityStore = useActivityStore();
const { isAdmin, isAnonymous } = storeToRefs(userStore);

const emit = defineEmits(["dragstart"]);

// activities from store
const { activities } = storeToRefs(activityStore);

// drag references
const dragTarget: Ref<EventTarget | null> = ref(null);
const dragItem: Ref<Activity | null> = ref(null);

// drag state
const isDragging = ref(false);

// sync built-in activities with cached activities
activityStore.sync();

/**
 * Checks if the route of an activity is currently being visited and panels are collapsed
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

const isSideBarOpen = computed(() => userStore.toggledSideBar !== "");

/**
 * Checks if an activity that has a panel should have the `is-active` prop
 */
function panelActivityIsActive(activity: Activity) {
    return isActiveSideBar(activity.id) || (activity.to !== null && isActiveRoute(activity.to));
}

/**
 * Evaluates the drop data and keeps track of the drop area
 */
function onDragEnter(evt: MouseEvent) {
    const eventData = eventStore.getDragData();
    if (eventData && !eventStore.multipleDragData) {
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
function onToggleSidebar(toggle: string = "", to: string | null = null) {
    // if an activity's dedicated panel/sideBar is already active
    // but the route is different, don't collapse
    if (toggle && to && !(route.path === to) && isActiveSideBar(toggle)) {
        return;
    }
    userStore.toggleSideBar(toggle);
}

watch(
    () => hashedUserId.value,
    () => {
        activityStore.sync();
    }
);
</script>

<template>
    <div class="d-flex">
        <div
            class="activity-bar d-flex flex-column no-highlight"
            data-description="activity bar"
            @dragover.prevent="onDragOver"
            @dragenter.prevent="onDragEnter"
            @dragleave.prevent="onDragLeave">
            <b-nav vertical class="flex-nowrap p-1 h-100 vertical-overflow">
                <draggable
                    :list="activities"
                    :class="{ 'activity-popper-disabled': isDragging }"
                    :force-fallback="true"
                    chosen-class="activity-chosen-class"
                    :delay="DRAG_DELAY"
                    drag-class="activity-drag-class"
                    ghost-class="activity-chosen-class"
                    @start="isDragging = true"
                    @end="isDragging = false">
                    <div v-for="(activity, activityIndex) in activities" :key="activityIndex">
                        <div v-if="activity.visible && (activity.anonymous || !isAnonymous)">
                            <UploadItem
                                v-if="activity.id === 'upload'"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :title="activity.title"
                                :tooltip="activity.tooltip" />
                            <InteractiveItem
                                v-else-if="activity.to && activity.id === 'interactivetools'"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :is-active="isActiveRoute(activity.to)"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :to="activity.to"
                                @click="onToggleSidebar()" />
                            <ActivityItem
                                v-else-if="activity.id === 'admin' || activity.panel"
                                :id="`activity-${activity.id}`"
                                :key="activity.id"
                                :icon="activity.icon"
                                :is-active="panelActivityIsActive(activity)"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :to="activity.to || ''"
                                @click="onToggleSidebar(activity.id, activity.to)" />
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
            <b-nav v-if="!isAnonymous" vertical class="activity-footer flex-nowrap p-1">
                <NotificationItem
                    v-if="isConfigLoaded && config.enable_notification_system"
                    id="activity-notifications"
                    icon="bell"
                    :is-active="isActiveSideBar('notifications') || isActiveRoute('/user/notifications')"
                    title="Notifications"
                    @click="onToggleSidebar('notifications')" />
                <ActivityItem
                    id="activity-settings"
                    icon="ellipsis-h"
                    :is-active="isActiveSideBar('settings')"
                    title="More"
                    tooltip="View additional activities"
                    @click="onToggleSidebar('settings')" />
                <ActivityItem
                    v-if="isAdmin"
                    id="activity-admin"
                    icon="user-cog"
                    :is-active="isActiveSideBar('admin')"
                    title="Admin"
                    tooltip="Administer this Galaxy"
                    variant="danger"
                    @click="onToggleSidebar('admin')" />
            </b-nav>
        </div>
        <FlexPanel v-if="isSideBarOpen" side="left" :collapsible="false">
            <ToolPanel v-if="isActiveSideBar('tools')" />
            <InvocationsPanel v-else-if="isActiveSideBar('invocation')" />
            <VisualizationPanel v-else-if="isActiveSideBar('visualizations')" />
            <MultiviewPanel v-else-if="isActiveSideBar('multiview')" />
            <NotificationsPanel v-else-if="isActiveSideBar('notifications')" />
            <SettingsPanel v-else-if="isActiveSideBar('settings')" />
            <AdminPanel v-else-if="isActiveSideBar('admin')" />
        </FlexPanel>
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

.activity-footer {
    border-top: $border-default;
    border-top-style: dotted;
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
