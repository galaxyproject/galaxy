<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import { GAlert, GButton, GCard, GCol, GFormCheckbox, GRow } from "@/component-library";
import {
    getNotificationsPreferencesFromServer,
    updateNotificationsPreferencesOnServer,
} from "@/components/User/Notifications/model/services";
import { useConfig } from "@/composables/config";
import { Toast } from "@/composables/toast";
import {
    browserSupportsPushNotifications,
    pushNotificationsEnabled,
    togglePushNotifications,
} from "@/composables/utils/pushNotifications";
import type { components } from "@/schema";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faExclamationCircle);

defineProps({
    headerSize: {
        type: String,
        default: "h-lg",
    },
});

type UserNotificationPreferences = components["schemas"]["UserNotificationPreferences"];

const { config } = useConfig(true);

const loading = ref(false);
const errorMessage = ref<string | null>(null);
const pushNotificationsGranted = ref(pushNotificationsEnabled());
const notificationsPreferences = ref<UserNotificationPreferences["preferences"]>({});

const categories = computed(() => Object.keys(notificationsPreferences.value));
const showPreferences = computed(() => {
    return !loading.value && config.value.enable_notification_system && notificationsPreferences.value;
});

const categoryDescriptionMap = {
    message: "You will receive notifications when someone sends you a message.",
    new_shared_item: "You will receive notifications when someone shares an item with you.",
};

async function getNotificationsPreferences() {
    loading.value = true;
    await getNotificationsPreferencesFromServer()
        .then((data) => {
            notificationsPreferences.value = data.preferences;
        })
        .catch((error: any) => {
            errorMessage.value = error;
        })
        .finally(() => {
            loading.value = false;
        });
}

async function updateNotificationsPreferences() {
    await updateNotificationsPreferencesOnServer({ preferences: notificationsPreferences.value })
        .then((data) => {
            notificationsPreferences.value = data.preferences;
            Toast.success("Notifications preferences updated");
        })
        .catch((error: any) => {
            errorMessage.value = error;
        });
}

function capitalizeWords(str: string): string {
    return str
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

async function onTogglePushNotifications() {
    pushNotificationsGranted.value = await togglePushNotifications();
}

watch(
    () => config.value.enable_notification_system,
    () => {
        if (config.value.enable_notification_system) {
            getNotificationsPreferences();
        }
    },
    { immediate: true }
);
</script>

<template>
    <section class="notifications-preferences">
        <h1 v-localize :class="headerSize">Manage notifications preferences</h1>

        <span v-if="config.enable_notification_system" v-localize class="mb-2">
            You can manage notifications channels and preferences here.
        </span>
        <span v-else v-localize class="mb-2"> You can manage push notifications preferences here. </span>

        <GAlert v-if="errorMessage" show dismissible fade variant="warning" @dismissed="errorMessage = null">
            {{ errorMessage }}
        </GAlert>

        <GAlert v-if="loading" class="m-2" show variant="info">
            <LoadingSpan message="Loading notifications preferences" />
        </GAlert>

        <GRow v-else-if="showPreferences" class="mx-1">
            <GCol v-for="category in categories" :key="category">
                <GCard class="my-2 px-2">
                    <GRow align-h="between" align-v="center">
                        <GCol cols="auto" class="mx-2">
                            <GRow>
                                <span v-localize class="category-title">{{ capitalizeWords(category) }}</span>
                            </GRow>
                            <GRow v-if="categoryDescriptionMap[category]">
                                <span v-localize class="category-description">
                                    {{ categoryDescriptionMap[category] }}
                                </span>
                            </GRow>
                        </GCol>
                        <GCol cols="auto" class="p-0">
                            <GFormCheckbox
                                v-model="notificationsPreferences[category].enabled"
                                v-b-tooltip.hover
                                :title="
                                    notificationsPreferences[category].enabled
                                        ? 'Disable notifications'
                                        : 'Enable notifications'
                                "
                                switch />
                        </GCol>
                    </GRow>
                    <GRow class="p-2">
                        <GCol
                            v-for="channel in Object.keys(notificationsPreferences[category].channels)"
                            :key="channel"
                            class="d-flex align-items-center">
                            <GFormCheckbox
                                v-model="notificationsPreferences[category].channels[channel]"
                                v-localize
                                :disabled="!notificationsPreferences[category].enabled">
                                {{ capitalizeWords(channel) }}
                            </GFormCheckbox>
                            <FontAwesomeIcon
                                v-if="channel === 'push'"
                                v-b-tooltip.hover="'Push notifications need to be enabled'"
                                class="mx-2"
                                icon="exclamation-circle" />
                        </GCol>
                    </GRow>
                </GCard>
            </GCol>
        </GRow>

        <GRow v-if="!loading" class="m-1" align-h="center">
            <GCard v-if="browserSupportsPushNotifications() && !pushNotificationsGranted" class="my-2">
                Allow push and tab notifications. To disable, revoke the site notification privilege in your browser.
                <GButton
                    v-b-tooltip.hover
                    class="mx-2"
                    title="Enable push notifications"
                    @click="onTogglePushNotifications">
                    Enable push notifications
                </GButton>
            </GCard>
            <GAlert
                v-else-if="browserSupportsPushNotifications() && pushNotificationsGranted"
                show
                variant="info"
                class="my-2">
                <FontAwesomeIcon icon="check-circle" />
                Push notifications are enabled. You can disable them by revoking the site notification privilege in your
                browser.
            </GAlert>
            <GAlert v-else show variant="warning" class="my-2">
                <FontAwesomeIcon icon="exclamation-circle" />
                Push notifications are not supported by this browser. You can still receive in-app notifications.
            </GAlert>
        </GRow>

        <GRow v-if="!loading && config.enable_notification_system" class="m-1" align-h="center">
            <AsyncButton :action="updateNotificationsPreferences" icon="save" variant="primary" size="md">
                <span v-localize>Save</span>
            </AsyncButton>
        </GRow>
    </section>
</template>

<style scoped lang="scss">
.category-title {
    font-weight: bold;
}

.category-description {
    font-size: 0.8rem;
    font-style: italic;
}
</style>
