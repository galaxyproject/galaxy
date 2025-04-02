<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog, faHourglassHalf, faRetweet } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup, BCollapse, BFormCheckbox } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { UserNotification } from "@/api/notifications";
import { useNotificationsStore } from "@/stores/notificationsStore";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import NotificationCard from "@/components/Notifications/NotificationCard.vue";
import NotificationsPreferences from "@/components/User/Notifications/NotificationsPreferences.vue";

library.add(faCog, faHourglassHalf, faRetweet);

const notificationsStore = useNotificationsStore();
const { notifications, loadingNotifications } = storeToRefs(notificationsStore);

interface Props {
    shouldOpenPreferences?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    shouldOpenPreferences: false,
});

const showUnread = ref(false);
const showShared = ref(false);
const preferencesOpen = ref(props.shouldOpenPreferences);
const selectedNotificationIds = ref<string[]>([]);

const haveSelected = computed(() => selectedNotificationIds.value.length > 0);
const filteredNotifications = computed(() => {
    return notifications.value.filter(filterNotifications);
});
const allSelected = computed(
    () => haveSelected.value && selectedNotificationIds.value.length === notifications.value.length
);

function filterNotifications(notification: UserNotification) {
    if (showUnread.value && showShared.value) {
        return !notification.seen_time && notification.category === "new_shared_item";
    } else if (showUnread.value) {
        return !notification.seen_time;
    } else if (showShared.value) {
        return notification.category === "new_shared_item";
    } else {
        return true;
    }
}

async function updateNotifications(changes: any) {
    await notificationsStore.updateBatchNotification({ notification_ids: selectedNotificationIds.value, changes });
    selectedNotificationIds.value = [];
}

function selectOrDeselectNotification(items: UserNotification[]) {
    const ids = items.map((item) => item.id);
    const selectedIds = selectedNotificationIds.value;
    const newSelectedIds = selectedIds.filter((id) => !ids.includes(id));
    if (newSelectedIds.length === selectedIds.length) {
        selectedNotificationIds.value = [...selectedIds, ...ids];
    } else {
        selectedNotificationIds.value = newSelectedIds;
    }
}

function togglePreferences() {
    preferencesOpen.value = !preferencesOpen.value;
}
</script>

<template>
    <div aria-labelledby="notifications-list" class="notifications-list-container">
        <div class="notifications-list-header">
            <Heading id="notifications-title" h1 separator inline size="xl" class="flex-grow-1 mb-2">
                Notifications
            </Heading>

            <BButton class="mb-2" variant="outline-primary" :pressed="preferencesOpen" @click="togglePreferences">
                <FontAwesomeIcon :icon="faCog" />
                Notifications preferences
            </BButton>
        </div>

        <BCollapse v-model="preferencesOpen">
            <div class="notifications-list-preferences card-container">
                <NotificationsPreferences v-if="preferencesOpen" header-size="h-md" :embedded="false" />
            </div>
        </BCollapse>

        <BAlert v-if="loadingNotifications" show>
            <LoadingSpan message="Loading notifications" />
        </BAlert>

        <BAlert v-else-if="notifications.length === 0" id="no-notifications" show variant="info">
            No notifications to show.
        </BAlert>

        <div v-else class="notifications-list-body">
            <div class="notifications-list-filter card-container">
                <div class="notifications-list-filter-selection">
                    <div>
                        <BFormCheckbox
                            :checked="allSelected"
                            :indeterminate="
                                selectedNotificationIds.length > 0 &&
                                selectedNotificationIds.length < notifications.length
                            "
                            @change="selectOrDeselectNotification(notifications)">
                            {{ haveSelected ? `${selectedNotificationIds.length} selected` : "Select all" }}
                        </BFormCheckbox>
                    </div>

                    <div v-if="haveSelected">
                        <BButton size="sm" variant="outline-primary" @click="updateNotifications({ seen: true })">
                            <FontAwesomeIcon icon="check" />
                            Mark as read
                        </BButton>

                        <BButton size="sm" variant="outline-primary" @click="updateNotifications({ deleted: true })">
                            <FontAwesomeIcon icon="trash" />
                            Delete
                        </BButton>
                    </div>
                </div>

                <div align-h="end" align-v="center">
                    <span class="mx-2"> Filters: </span>

                    <BButtonGroup>
                        <BButton
                            id="show-unread-filter"
                            size="sm"
                            :pressed="showUnread"
                            variant="outline-primary"
                            @click="showUnread = !showUnread">
                            <FontAwesomeIcon icon="check" />
                            Unread
                        </BButton>

                        <BButton
                            id="show-shared-filter"
                            size="sm"
                            :pressed="showShared"
                            variant="outline-primary"
                            @click="showShared = !showShared">
                            <FontAwesomeIcon icon="retweet" />
                            Shared
                        </BButton>
                    </BButtonGroup>
                </div>
            </div>

            <BAlert v-show="filteredNotifications.length === 0" show variant="info">
                No matching notifications with current filters.
            </BAlert>

            <TransitionGroup
                v-show="filteredNotifications.length > 0"
                name="notifications-list"
                class="notifications-list"
                tag="div">
                <NotificationCard
                    v-for="notification in filteredNotifications"
                    :key="notification.id"
                    selectable
                    unread-border
                    :notification="notification"
                    :selected="selectedNotificationIds?.includes(notification.id)"
                    @select="selectOrDeselectNotification" />
            </TransitionGroup>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.notifications-list-container {
    .notifications-list-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .notifications-list-preferences {
        margin: 0 0.5rem 1rem 0.5rem;
    }

    .notifications-list-body {
        .notifications-list {
            padding-bottom: 0.5rem;
        }

        .notifications-list-filter {
            display: flex;
            align-items: center;
            justify-content: space-between;

            .notifications-list-filter-selection {
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
        }
    }
}

.notifications-list-enter-active {
    transition: all 0.5s ease;
}

.notifications-list-leave-active {
    transition: all 0.3s ease;
}

.notifications-list-enter {
    opacity: 0;
    transform: translateY(-2rem);
}

.notifications-list-leave-to {
    opacity: 0;
    transform: translateX(2rem);
}
</style>
