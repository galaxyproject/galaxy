<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInbox } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCol, BRow } from "bootstrap-vue";
import { computed } from "vue";

import { type MessageNotification } from "@/api/notifications";
import { useMarkdown } from "@/composables/markdown";

import Heading from "@/components/Common/Heading.vue";
import NotificationActions from "@/components/Notifications/NotificationActions.vue";

library.add(faInbox);

type PartialNotification = Partial<MessageNotification> & { content: MessageNotification["content"] };

type Options =
    | {
          previewMode?: false;
          notification: MessageNotification;
      }
    | {
          previewMode: true;
          notification: PartialNotification;
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
</script>

<template>
    <BCol>
        <BRow align-v="center">
            <Heading size="md" :bold="!props.options.notification.seen_time" class="mb-0">
                <FontAwesomeIcon :class="`text-${notificationVariant}`" icon="inbox" />
                {{ props.options.notification?.content?.subject }}
            </Heading>
            <NotificationActions v-if="!props.options.previewMode" :notification="props.options.notification" />
        </BRow>
        <BRow>
            <span id="notification-message" v-html="renderMarkdown(props.options.notification.content.message)" />
        </BRow>
    </BCol>
</template>
