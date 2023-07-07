<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
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
        <div class="d-flex justify-content-between">
            <Heading id="notifications-title">Notifications and Broadcasts</Heading>
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
        </div>

        <BroadcastsList />
    </div>
</template>
