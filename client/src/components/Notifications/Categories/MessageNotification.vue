<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInbox } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { type MessageNotification, type MessageNotificationCreateData } from "@/api/notifications";
import { useMarkdown } from "@/composables/markdown";

import NotificationActions from "@/components/Notifications/NotificationActions.vue";

library.add(faInbox);

type Options =
    | {
          previewMode?: false;
          notification: MessageNotification;
      }
    | {
          previewMode: true;
          notification: MessageNotificationCreateData;
      };

const props = defineProps<{
    options: Options;
}>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const notificationVariant = computed(() => {
    switch (props.options.notification.variant) {
        case "urgent":
            return "danger";
        default:
            return props.options.notification.variant;
    }
});

const notificationSeen = computed(() => {
    return "seen_time" in props.options.notification && !!props.options.notification.seen_time;
});
</script>

<template>
    <div class="notification-container">
        <div class="notification-header">
            <div :class="!notificationSeen ? 'font-weight-bold' : ''" class="notification-title">
                <FontAwesomeIcon :class="`text-${notificationVariant}`" :icon="faInbox" fixed-width size="sm" />
                {{ props.options.notification?.content?.subject }}
            </div>
        </div>

        <NotificationActions
            v-if="!props.options.previewMode"
            class="notification-actions"
            :notification="props.options.notification" />

        <span
            id="notification-message"
            class="notification-message"
            v-html="renderMarkdown(props.options.notification.content.message)" />
    </div>
</template>

<style scoped lang="scss">
@import "style.scss";
</style>
