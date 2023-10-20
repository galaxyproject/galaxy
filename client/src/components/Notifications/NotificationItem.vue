<script setup lang="ts">
import { type UserNotification } from "@/api/notifications";

import MessageNotification from "./Categories/MessageNotification.vue";
import SharedItemNotification from "./Categories/SharedItemNotification.vue";

const props = defineProps<{
    notification: UserNotification;
}>();
</script>

<template>
    <SharedItemNotification
        v-if="props.notification.category === 'new_shared_item'"
        :notification="props.notification" />

    <MessageNotification v-else :options="{ notification: props.notification }" />
</template>
