<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCircle } from "@fortawesome/free-solid-svg-icons";
import { BFormCheckbox } from "bootstrap-vue";

import { type UserNotification } from "@/api/notifications";

import MessageNotification from "./Categories/MessageNotification.vue";
import SharedItemNotification from "./Categories/SharedItemNotification.vue";

library.add(faCircle);

const props = defineProps<{
    selected?: boolean;
    selectable?: boolean;
    unreadBorder?: boolean;
    notification: UserNotification;
}>();

const emit = defineEmits(["select"]);
</script>

<template>
    <div
        class="notification-card card-container"
        :class="props.unreadBorder && !props.notification.seen_time ? 'border-dark unread-notification' : ''">
        <BFormCheckbox
            v-if="props.selectable"
            class="notification-card-select"
            :checked="props.selected"
            size="sm"
            @change="emit('select', [props.notification])" />

        <SharedItemNotification
            v-if="props.notification.category === 'new_shared_item'"
            :notification="props.notification" />

        <MessageNotification v-else :options="{ notification: props.notification }" />
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.notification-card {
    display: flex;

    .notification-card-select {
        padding-top: 0.35rem;
    }
}
</style>
