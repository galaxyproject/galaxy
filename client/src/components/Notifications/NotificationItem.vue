<script setup lang="ts">
import { computed } from "vue";
import type { UserNotification } from ".";
import MessageNotificationComponent from "./Categories/MessageNotification.vue";
import SharedItemNotificationComponent from "./Categories/SharedItemNotification.vue";

/**
 * A map of notification categories to their corresponding Vue components.
 */
const notificationComponentMap = {
    message: MessageNotificationComponent,
    new_shared_item: SharedItemNotificationComponent,
};

const props = defineProps<{
    notification: UserNotification;
}>();

const notificationComponent = computed(() => notificationComponentMap[props.notification.category]);
</script>

<template>
    <component :is="notificationComponent" :notification="props.notification" />
</template>
