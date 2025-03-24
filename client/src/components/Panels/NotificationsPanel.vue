<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckDouble } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useNotificationsStore } from "@/stores/notificationsStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import NotificationCard from "@/components/Notifications/NotificationCard.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

library.add(faCheckDouble);

const { confirm } = useConfirmDialog();

const notificationsStore = useNotificationsStore();
const { notifications, loadingNotifications } = storeToRefs(notificationsStore);

const unreadNotifications = computed(() => {
    return notifications.value.filter((notification) => !notification.seen_time);
});

async function onMarkAllAsRead() {
    const confirmed = await confirm("您确定要将所有未读通知标记为已读吗？", {
        title: "将所有未读通知标记为已读？",
    });

    if (confirmed) {
        await notificationsStore.updateBatchNotification({
            notification_ids: unreadNotifications.value.map((n) => n.id),
            changes: { seen: true },
        });
    }
}
</script>

<template>
    <ActivityPanel title="Unread Notifications" go-to-all-title="All notifications" href="/user/notifications">
        <template v-slot:header-buttons>
            <BButtonGroup>
                <BButton
                    v-b-tooltip.bottom.hover
                    data-description="mark all as read"
                    size="sm"
                    variant="link"
                    title="Mark all as read"
                    @click="onMarkAllAsRead">
                    <FontAwesomeIcon :icon="faCheckDouble" fixed-width />
                </BButton>
            </BButtonGroup>
        </template>

        <template v-slot:header>
            <div v-if="!loadingNotifications && unreadNotifications.length">
                You have {{ unreadNotifications.length }} unread notifications.
            </div>
        </template>

        <BAlert v-if="loadingNotifications" key="loading-notifications" show>
            <LoadingSpan message="Loading notifications" />
        </BAlert>

        <BAlert v-else-if="!unreadNotifications.length" key="no-notifications-message" show>
            No unread notifications to show.
        </BAlert>

        <TransitionGroup class="notifications-box-list" name="notifications-box-list" tag="div">
            <div v-for="notification in unreadNotifications" :key="notification.id" class="notifications-box-card">
                <NotificationCard :notification="notification" />
            </div>
        </TransitionGroup>
    </ActivityPanel>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.notifications-box-card {
    background-color: $body-bg;
}

.notifications-box-list {
    overflow-y: scroll;
}

.notifications-box-list-enter-active {
    transition: all 0.5s ease;
}

.notifications-box-list-leave-active {
    transition: all 0.3s ease;
}

.notifications-box-list-enter {
    opacity: 0;
    transform: translateY(-2rem);
}

.notifications-box-list-leave-to {
    opacity: 0;
    transform: translateY(-1rem);
}
</style>
