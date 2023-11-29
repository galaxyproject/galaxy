<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import BroadcastsList from "@/components/admin/Notifications/BroadcastsList.vue";
import Heading from "@/components/Common/Heading.vue";

const router = useRouter();

function goToCreateNewNotification() {
    router.push("/admin/notifications/create_new_notification");
}

function goToCreateNewBroadcast() {
    router.push("/admin/notifications/create_new_broadcast");
}
</script>

<template>
    <div aria-labelledby="notifications-managements">
        <Heading id="notifications-title" h1 separator inline class="flex-grow-1">
            Notifications and Broadcasts
        </Heading>

        <p>
            As an admin, you can send individual notifications to users (groups or roles), or display
            <i>broadcast notifications</i> to all users (even anonymous users).
        </p>

        <div>
            <BButton class="mb-2" variant="outline-primary" @click="goToCreateNewNotification">
                <FontAwesomeIcon icon="plus" />
                Send new notification
            </BButton>

            <BButton class="mb-2" variant="outline-primary" @click="goToCreateNewBroadcast">
                <FontAwesomeIcon icon="plus" />
                Create new broadcast
            </BButton>
        </div>

        <BroadcastsList class="mt-2" />
    </div>
</template>
