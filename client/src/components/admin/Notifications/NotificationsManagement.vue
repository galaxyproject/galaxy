<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";

import BroadcastsList from "@/components/admin/Notifications/BroadcastsList.vue";
import Heading from "@/components/Common/Heading.vue";

const router = useRouter();
const { config, isConfigLoaded } = useConfig();

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

        <div v-if="isConfigLoaded && config.enable_notification_system">
            <div>
                <BButton
                    id="send-notification-button"
                    class="mb-2"
                    variant="outline-primary"
                    @click="goToCreateNewNotification">
                    <FontAwesomeIcon icon="plus" />
                    Send new notification
                </BButton>

                <BButton
                    id="create-broadcast-button"
                    class="mb-2"
                    variant="outline-primary"
                    @click="goToCreateNewBroadcast">
                    <FontAwesomeIcon icon="plus" />
                    Create new broadcast
                </BButton>
            </div>

            <BroadcastsList class="mt-2" />
        </div>
        <BAlert v-else variant="warning" show>
            The notification system is disabled. To enable it, set the
            <code>enable_notification_system</code> option to <code>true</code> in the Galaxy configuration file.
        </BAlert>
    </div>
</template>
