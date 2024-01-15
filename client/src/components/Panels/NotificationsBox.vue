<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckDouble } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfirmDialog } from "@/composables/confirmDialog";
import { useNotificationsStore } from "@/stores/notificationsStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import NotificationItem from "@/components/Notifications/NotificationItem.vue";

library.add(faCheckDouble);

const router = useRouter();
const { confirm } = useConfirmDialog();

const notificationsStore = useNotificationsStore();
const { notifications, loadingNotifications } = storeToRefs(notificationsStore);

const unreadNotifications = computed(() => {
    return notifications.value.filter((notification) => !notification.seen_time);
});

async function onMarkAllAsRead() {
    const confirmed = await confirm("Are you sure you want to mark all unread notifications as read?", {
        title: "Mark all unread notifications as read?",
    });

    if (confirmed) {
        await notificationsStore.updateBatchNotification({
            notification_ids: unreadNotifications.value.map((n) => n.id),
            changes: { seen: true },
        });
    }
}

function goToAllNotifications() {
    router.push("/user/notifications");
}
</script>

<template>
    <div class="unified-panel" data-description="notifications" aria-labelledby="notifications-box-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <h2 v-localize class="m-1 h-sm">Unread notifications</h2>

                    <BButtonGroup>
                        <BButton
                            v-if="unreadNotifications.length > 0"
                            v-b-tooltip.bottom.hover
                            data-description="mark all as read"
                            size="sm"
                            variant="link"
                            title="Mark all as read"
                            @click="onMarkAllAsRead">
                            <FontAwesomeIcon :icon="faCheckDouble" fixed-width />
                        </BButton>
                    </BButtonGroup>
                </nav>

                <BAlert v-if="loadingNotifications" key="loading-notifications" show class="mx-2">
                    <LoadingSpan message="Loading notifications" />
                </BAlert>

                <div v-else-if="unreadNotifications.length" class="unified-panel-header-description mx-3 my-2">
                    You have {{ unreadNotifications.length }} unread notifications.
                </div>

                <BAlert v-else key="no-notifications-message" show class="mx-2">
                    No unread notifications to show.
                </BAlert>
            </div>
        </div>

        <TransitionGroup name="notifications-box-list" tag="div" class="unified-panel-body">
            <div v-for="notification in unreadNotifications" :key="notification.id" class="notifications-box-card">
                <NotificationItem :notification="notification" />
            </div>
        </TransitionGroup>

        <BButton class="m-2" variant="primary" @click="goToAllNotifications"> All notifications </BButton>
    </div>
</template>

<style lang="scss" scoped>
.notifications-box-card {
    margin: 0.5rem 0.25rem;
    padding: 0.5rem 0.75rem;
    background-color: white;
    border: 1px solid #e5e5e5;
    border-radius: 0.5rem;
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
