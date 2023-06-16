<script setup lang="ts">
import { computed } from "vue";
import { BCol, BRow } from "bootstrap-vue";
import Heading from "@/components/Common/Heading.vue";
import { faInbox } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import NotificationActions from "@/components/Notifications/NotificationActions.vue";
import type { MessageNotification } from "@/components/Notifications";
import { useMarkdown } from "@/composables/markdown";

library.add(faInbox);

interface Props {
    notification: MessageNotification;
}

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const props = defineProps<Props>();

const notificationVariant = computed(() => {
    switch (props.notification.variant) {
        case "urgent":
            return "danger";
        default:
            return props.notification.variant;
    }
});
</script>

<template>
    <BCol>
        <BRow align-v="center">
            <Heading size="md" :bold="!notification.seen_time" class="mb-0">
                <FontAwesomeIcon :class="`text-${notificationVariant}`" icon="inbox" />
                {{ notification.content.subject }}
            </Heading>
            <NotificationActions :notification="notification" />
        </BRow>
        <BRow>
            <span id="notification-message" v-html="renderMarkdown(notification.content.message)" />
        </BRow>
    </BCol>
</template>
