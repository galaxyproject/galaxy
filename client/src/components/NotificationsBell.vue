<script setup>
import { storeToRefs } from "pinia";
import { faBell } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
import { useNotificationsStore } from "@/stores/notificationsStore";
import ActivityItem from "@/components/ActivityBar/ActivityItem.vue";

//@ts-ignore
library.add(faBell);

defineProps({
    tooltipPlacement: {
        type: String,
        default: "right",
    },
});

const { totalUnreadCount } = storeToRefs(useNotificationsStore());
</script>

<template>
    <ActivityItem
        id="activity-notifications"
        :tooltip-placement="tooltipPlacement"
        :indicator="!!totalUnreadCount"
        :icon="faBell"
        :tooltip="
            totalUnreadCount ? `You have ${totalUnreadCount} unread notifications` : 'You have no unread notifications'
        "
        to="/notifications" />
</template>
