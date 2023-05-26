<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { BAlert, BRow, BCol, BFormCheckbox, BButton, BButtonGroup, BCard, BCollapse } from "bootstrap-vue";
import type { components } from "@/schema";
import LoadingSpan from "@/components/LoadingSpan.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useNotificationsStore } from "@/stores/notificationsStore";
import { faCircle, faHourglassHalf } from "@fortawesome/free-solid-svg-icons";
import MessageNotification from "@/components/Notifications/Categories/MessageNotification.vue";
import NotificationsPreferences from "@/components/User/Notifications/NotificationsPreferences.vue";
import SharedItemNotification from "@/components/Notifications/Categories/SharedItemNotification.vue";

library.add(faCircle, faHourglassHalf);

type UserNotificationResponse = components["schemas"]["UserNotificationResponse"];

const notificationsStore = useNotificationsStore();
const { notifications, loadingNotifications } = storeToRefs(notificationsStore);

const showUnread = ref(false);
const showFavorites = ref(false);
const preferencesOpen = ref(false);
const selectedNotificationIds = ref<string[]>([]);

const haveSelected = computed(() => selectedNotificationIds.value.length > 0);
const filteredNotifications = computed(() => {
    return notifications.value.filter(filterNotifications);
});
const allSelected = computed(
    () => haveSelected.value && selectedNotificationIds.value.length === notifications.value.length
);

function filterNotifications(notification: UserNotificationResponse) {
    if (showUnread.value && showFavorites.value) {
        return !notification.seen_time && notification.favorite;
    } else if (showUnread.value) {
        return !notification.seen_time;
    } else if (showFavorites.value) {
        return notification.favorite;
    } else {
        return true;
    }
}

async function updateNotifications(changes: any) {
    await notificationsStore.updateBatchNotification({ notification_ids: selectedNotificationIds.value, changes });
    selectedNotificationIds.value = [];
}

function selectOrDeselectNotification(items: UserNotificationResponse[]) {
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
    <div aria-labelledby="notifications-list">
        <div class="d-flex justify-content-between">
            <h1 id="notifications-title" class="h-lg">Notifications</h1>
            <BButton class="mb-2" variant="outline-primary" :pressed="preferencesOpen" @click="togglePreferences">
                <FontAwesomeIcon icon="cog" />
                Notifications preferences
            </BButton>
        </div>

        <BCollapse v-model="preferencesOpen">
            <BCard class="m-2">
                <NotificationsPreferences header-size="h-md" />
            </BCard>
        </BCollapse>

        <BAlert v-if="loadingNotifications" show>
            <LoadingSpan message="Loading notifications" />
        </BAlert>

        <BAlert v-else-if="notifications.length === 0" show variant="info"> No notifications to show. </BAlert>

        <div v-else class="mx-1">
            <BCard class="mb-2">
                <BRow class="align-items-center" no-gutters>
                    <BCol cols="1">
                        <BFormCheckbox
                            :checked="allSelected"
                            :indeterminate="
                                selectedNotificationIds.length > 0 &&
                                selectedNotificationIds.length < notifications.length
                            "
                            @change="selectOrDeselectNotification(notifications)">
                            {{ haveSelected ? `${selectedNotificationIds.length} selected` : "Select all" }}
                        </BFormCheckbox>
                    </BCol>
                    <BCol v-if="haveSelected">
                        <BButton size="sm" variant="outline-primary" @click="updateNotifications({ seen: true })">
                            <FontAwesomeIcon icon="check" />
                            Mark as read
                        </BButton>
                        <BButton size="sm" variant="outline-primary" @click="updateNotifications({ deleted: true })">
                            <FontAwesomeIcon icon="trash" />
                            Delete
                        </BButton>
                    </BCol>
                    <BCol>
                        <BRow align-h="end" align-v="center">
                            <span class="mx-2"> Filters: </span>
                            <BButtonGroup>
                                <BButton
                                    size="sm"
                                    :pressed="showUnread"
                                    variant="outline-primary"
                                    @click="showUnread = !showUnread">
                                    <FontAwesomeIcon icon="check" />
                                    Unread
                                </BButton>
                                <BButton
                                    size="sm"
                                    :pressed="showFavorites"
                                    variant="outline-primary"
                                    @click="showFavorites = !showFavorites">
                                    <FontAwesomeIcon icon="star" />
                                    Favorites
                                </BButton>
                            </BButtonGroup>
                        </BRow>
                    </BCol>
                </BRow>
            </BCard>

            <BAlert v-show="filteredNotifications.length === 0" show variant="info">
                No matching notifications with current filters.
            </BAlert>

            <TransitionGroup name="notifications-list" tag="div">
                <BCard
                    v-for="item in filteredNotifications"
                    v-show="filteredNotifications.length > 0"
                    :key="item.id"
                    class="my-2 notification-card"
                    :class="!item.seen_time ? 'border-dark' : ''">
                    <BRow align-h="start" align-v="center">
                        <BCol cols="auto">
                            <BButtonGroup>
                                <FontAwesomeIcon
                                    v-if="!item.seen_time"
                                    size="sm"
                                    class="unread-status position-absolute align-self-center mr-1"
                                    icon="circle" />
                                <BFormCheckbox
                                    :checked="selectedNotificationIds.includes(item.id)"
                                    @change="selectOrDeselectNotification([item])" />
                            </BButtonGroup>
                        </BCol>
                        <SharedItemNotification v-if="item.category === 'new_shared_item'" :notification="item" />
                        <MessageNotification v-else :notification="item" />
                    </BRow>
                </BCard>
            </TransitionGroup>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.unread-status {
    left: -1rem;
    color: $brand-primary;
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
