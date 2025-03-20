<script setup lang="ts">
import { type IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faBell, faEllipsisH, faUserCog } from "@fortawesome/free-solid-svg-icons";
import { watchImmediate } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { computed, type Ref, ref } from "vue";
import { useRoute } from "vue-router/composables";
import draggable from "vuedraggable";

import { useConfig } from "@/composables/config";
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

const props = withDefaults(
    defineProps<{
        defaultActivities?: Activity[];
        activityBarId?: string;
        specialActivities?: Activity[];
        showAdmin?: boolean;
        optionsTitle?: string;
        optionsTooltip?: string;
        optionsHeading?: string;
        optionsIcon?: IconDefinition;
        optionsSearchPlaceholder?: string;
        initialActivity?: string;
        hidePanel?: boolean;
    }>(),
    {
        defaultActivities: undefined,
        activityBarId: "default",
        specialActivities: () => [],
        showAdmin: true,
        optionsTitle: "More",
        optionsHeading: "Additional Activities",
        optionsIcon: () => faEllipsisH,
        optionsSearchPlaceholder: "Search Activities",
        optionsTooltip: "View additional activities",
        initialActivity: undefined,
        hidePanel: false,
    }
);

// require user to long click before dragging
const DRAG_DELAY = 50;

const { config, isConfigLoaded } = useConfig();

const route = useRoute();
const userStore = useUserStore();

const eventStore = useEventStore();
const activityStore = useActivityStore(props.activityBarId);

if (props.initialActivity) {
    activityStore.toggledSideBar = props.initialActivity;
}

watchImmediate(
    () => props.defaultActivities,
    (defaults) => {
        if (defaults) {
            activityStore.overrideDefaultActivities(defaults);
        } else {
            activityStore.resetDefaultActivities();
        }
    }
);

const { isAdmin, isAnonymous } = storeToRefs(userStore);

const emit = defineEmits<{
    (e: "dragstart", dragItem: Activity | null): void;
    (e: "activityClicked", activityId: string): void;
}>();

// activities from store
const { activities, isSideBarOpen } = storeToRefs(activityStore);

// drag references
const dragTarget: Ref<EventTarget | null> = ref(null);
const dragItem: Ref<Activity | null> = ref(null);

// drag state
const isDragging = ref(false);

/**
 * Checks if the route of an activity is currently being visited and panels are collapsed
 */
function isActiveRoute(activityTo?: string | null) {
    return route.path === activityTo && isActiveSideBar("");
}

/**
 * Checks if a panel has been expanded
 */
function isActiveSideBar(menuKey: string) {
    return activityStore.toggledSideBar === menuKey;
}

/**
 * Checks if an activity that has a panel should have the `is-active` prop
 */
function panelActivityIsActive(activity: Activity) {
    return isActiveSideBar(activity.id) || isActiveRoute(activity.to);
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
function toggleSidebar(toggle: string = "", to: string | null = null) {
    // if an activity's dedicated panel/sideBar is already active
    // but the route is different, don't collapse
    if (toggle && to && !(route.path === to) && isActiveSideBar(toggle)) {
        return;
    }
    activityStore.toggleSideBar(toggle);
}

function onActivityClicked(activity: Activity) {
    if (activity.click) {
        emit("activityClicked", activity.id);
    } else {
        toggleSidebar();
    }
}

function setActiveSideBar(key: string) {
    activityStore.toggledSideBar = key;
}

const canDrag = computed(() => {
    return isActiveSideBar("settings");
});

defineExpose({
    isActiveSideBar,
    setActiveSideBar,
});
</script>

<template>
    <div class="d-flex">
        <!-- while this warning is correct, it is hiding too many other errors -->
        <!-- eslint-disable-next-line vuejs-accessibility/no-static-element-interactions -->
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
                    :disabled="!canDrag"
                    :force-fallback="true"
                    chosen-class="activity-chosen-class"
                    :delay="DRAG_DELAY"
                    drag-class="activity-drag-class"
                    ghost-class="activity-chosen-class"
                    @start="isDragging = true"
                    @end="isDragging = false">
                    <div
                        v-for="(activity, activityIndex) in activities"
                        :key="activityIndex"
                        :class="{ 'can-drag': canDrag }">
                        <div v-if="activity.visible && (activity.anonymous || !isAnonymous)">
                            <UploadItem
                                v-if="activity.id === 'upload'"
                                :id="`${activity.id}`"
                                :key="activity.id"
                                :activity-bar-id="props.activityBarId"
                                :icon="activity.icon"
                                :title="activity.title"
                                :tooltip="activity.tooltip" />
                            <InteractiveItem
                                v-else-if="activity.to && activity.id === 'interactivetools'"
                                :id="`${activity.id}`"
                                :key="activity.id"
                                :activity-bar-id="props.activityBarId"
                                :icon="activity.icon"
                                :is-active="isActiveRoute(activity.to)"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :to="activity.to"
                                @click="toggleSidebar()" />
                            <ActivityItem
                                v-else-if="activity.id === 'admin' || activity.panel"
                                :id="`${activity.id}`"
                                :key="activity.id"
                                :activity-bar-id="props.activityBarId"
                                :icon="activity.icon"
                                :is-active="panelActivityIsActive(activity)"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :to="activity.to || ''"
                                @click="toggleSidebar(activity.id, activity.to)" />
                            <ActivityItem
                                v-else
                                :id="`${activity.id}`"
                                :key="activity.id"
                                :activity-bar-id="props.activityBarId"
                                :icon="activity.icon"
                                :is-active="isActiveRoute(activity.to)"
                                :title="activity.title"
                                :tooltip="activity.tooltip"
                                :to="activity.to ?? undefined"
                                :variant="activity.variant"
                                @click="onActivityClicked(activity)" />
                        </div>
                    </div>
                </draggable>
            </b-nav>
            <b-nav v-if="!isAnonymous" vertical class="activity-footer flex-nowrap p-1">
                <NotificationItem
                    v-if="isConfigLoaded && config.enable_notification_system"
                    id="notifications"
                    :activity-bar-id="props.activityBarId"
                    :icon="faBell"
                    :is-active="isActiveSideBar('notifications') || isActiveRoute('/user/notifications')"
                    title="Notifications"
                    @click="toggleSidebar('notifications')" />
                <ActivityItem
                    id="settings"
                    :activity-bar-id="props.activityBarId"
                    :icon="props.optionsIcon"
                    :is-active="isActiveSideBar('settings')"
                    :title="props.optionsTitle"
                    :tooltip="props.optionsTooltip"
                    @click="toggleSidebar('settings')" />
                <ActivityItem
                    v-if="isAdmin && showAdmin"
                    id="admin"
                    :activity-bar-id="props.activityBarId"
                    :icon="faUserCog"
                    :is-active="isActiveSideBar('admin')"
                    title="Admin"
                    tooltip="Administer this Galaxy"
                    variant="danger"
                    @click="toggleSidebar('admin')" />
                <template v-for="activity in props.specialActivities">
                    <ActivityItem
                        v-if="activity.panel"
                        :id="`${activity.id}`"
                        :key="activity.id"
                        :activity-bar-id="props.activityBarId"
                        :icon="activity.icon"
                        :is-active="panelActivityIsActive(activity)"
                        :title="activity.title"
                        :tooltip="activity.tooltip"
                        :to="activity.to || ''"
                        :variant="activity.variant"
                        @click="toggleSidebar(activity.id, activity.to)" />
                    <ActivityItem
                        v-else
                        :id="`${activity.id}`"
                        :key="activity.id"
                        :activity-bar-id="props.activityBarId"
                        :icon="activity.icon"
                        :is-active="isActiveRoute(activity.to)"
                        :title="activity.title"
                        :tooltip="activity.tooltip"
                        :to="activity.to ?? undefined"
                        :variant="activity.variant"
                        @click="onActivityClicked(activity)" />
                </template>
            </b-nav>
        </div>
        <FlexPanel v-if="isSideBarOpen && !hidePanel" side="left" :collapsible="false">
            <ToolPanel v-if="isActiveSideBar('tools')" />
            <InvocationsPanel v-else-if="isActiveSideBar('invocation')" :activity-bar-id="props.activityBarId" />
            <VisualizationPanel v-else-if="isActiveSideBar('visualizations')" />
            <MultiviewPanel v-else-if="isActiveSideBar('multiview')" />
            <NotificationsPanel v-else-if="isActiveSideBar('notifications')" />
            <SettingsPanel
                v-else-if="isActiveSideBar('settings')"
                :activity-bar-id="props.activityBarId"
                :heading="props.optionsHeading"
                :search-placeholder="props.optionsSearchPlaceholder"
                @activityClicked="(id) => emit('activityClicked', id)" />
            <AdminPanel v-else-if="isActiveSideBar('admin')" />
            <slot name="side-panel" :is-active-side-bar="isActiveSideBar"></slot>
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

.can-drag {
    border-radius: 12px;
    border: 1px;
    outline: dashed darkgray;
    outline-offset: -3px;
}
</style>
