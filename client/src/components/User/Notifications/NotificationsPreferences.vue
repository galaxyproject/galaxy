<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExclamationCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BFormCheckbox } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import {
    getNotificationsPreferencesFromServer,
    updateNotificationsPreferencesOnServer,
    type UserNotificationPreferencesExtended,
} from "@/api/notifications.preferences";
import { useConfig } from "@/composables/config";
import { Toast } from "@/composables/toast";
import {
    browserSupportsPushNotifications,
    pushNotificationsEnabled,
    togglePushNotifications,
} from "@/composables/utils/pushNotifications";

import AsyncButton from "@/components/Common/AsyncButton.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faExclamationCircle);

interface NotificationsPreferencesProps {
    embedded?: boolean;
    headerSize?: string;
}

const props = withDefaults(defineProps<NotificationsPreferencesProps>(), {
    embedded: true,
    headerSize: "h-lg",
});

const { config } = useConfig(true);

const loading = ref(false);
const errorMessage = ref<string | null>(null);
const pushNotificationsGranted = ref(pushNotificationsEnabled());
const notificationsPreferences = ref<UserNotificationPreferencesExtended["preferences"]>({});
const supportedChannels = ref<string[]>([]);

const categories = computed(() => Object.keys(notificationsPreferences.value));
const showPreferences = computed(() => {
    return !loading.value && config.value.enable_notification_system && notificationsPreferences.value;
});

const categoryDescriptionMap: Record<string, string> = {
    message: `
        You will receive these notifications only when your Galaxy administrators send you a message.
        Please note that for certain critical or urgent messages, you will receive notifications even if you have disabled this channel.
    `,
    new_shared_item:
        "You will receive these notifications when someone shares an item with you i.e. a history, workflow, visualization, etc.",
};

async function getNotificationsPreferences() {
    loading.value = true;
    await getNotificationsPreferencesFromServer()
        .then((data) => {
            supportedChannels.value = data.supportedChannels;
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
        <Heading
            h1
            :separator="props.embedded"
            inline
            size="xl"
            class="notifications-preferences-header"
            :class="headerSize">
            Manage notifications preferences
        </Heading>

        <div v-if="config.enable_notification_system" v-localize class="notifications-preferences-description">
            You can manage notifications channels and preferences here.
        </div>

        <div v-else v-localize class="notifications-preferences-description">
            You can manage push notifications preferences here.
        </div>

        <BAlert v-if="errorMessage" show dismissible fade variant="warning" @dismissed="errorMessage = null">
            {{ errorMessage }}
        </BAlert>

        <BAlert v-if="loading" class="m-2" show variant="info">
            <LoadingSpan message="Loading notifications preferences" />
        </BAlert>

        <div v-else-if="showPreferences" class="notifications-preferences-body">
            <div v-for="category in categories" :key="category" class="card-container">
                <div class="category-header">
                    <BFormCheckbox
                        v-model="notificationsPreferences[category].enabled"
                        v-b-tooltip.hover
                        :title="
                            notificationsPreferences[category].enabled
                                ? 'Disable notifications'
                                : 'Enable notifications'
                        "
                        switch>
                        <span v-localize class="category-title">{{ capitalizeWords(category) }}</span>
                    </BFormCheckbox>
                </div>

                <div v-if="categoryDescriptionMap[category]" v-localize class="category-description">
                    {{ categoryDescriptionMap[category] }}
                </div>

                <div v-for="channel in supportedChannels" :key="channel" class="category-channel">
                    <BFormCheckbox
                        v-model="notificationsPreferences[category].channels[channel]"
                        v-localize
                        :disabled="!notificationsPreferences[category].enabled">
                        {{ capitalizeWords(channel) }}
                    </BFormCheckbox>

                    <FontAwesomeIcon
                        v-if="channel === 'push'"
                        v-b-tooltip.hover="'Push notifications need to be enabled'"
                        class="mx-2"
                        icon="exclamation-circle" />
                </div>
            </div>
        </div>

        <div
            v-if="!loading && browserSupportsPushNotifications() && !pushNotificationsGranted"
            class="card-container push-notifications-notice">
            Allow push and tab notifications. To disable, revoke the site notification privilege in your browser.
            <BButton
                v-b-tooltip.hover
                class="mx-2"
                title="Enable push notifications"
                @click="onTogglePushNotifications">
                Enable push notifications
            </BButton>
        </div>

        <BAlert
            v-else-if="!loading && browserSupportsPushNotifications() && pushNotificationsGranted"
            show
            variant="info"
            class="my-2">
            <FontAwesomeIcon icon="check-circle" />
            Push notifications are enabled. You can disable them by revoking the site notification privilege in your
            browser.
        </BAlert>

        <BAlert v-else-if="!loading" show variant="warning" class="my-2">
            <FontAwesomeIcon icon="exclamation-circle" />
            Push notifications are not supported by this browser. You can still receive in-app notifications.
        </BAlert>

        <div v-if="!loading && config.enable_notification_system" class="d-flex justify-content-center">
            <AsyncButton :action="updateNotificationsPreferences" icon="save" variant="primary" size="md">
                <span v-localize>Save</span>
            </AsyncButton>
        </div>
    </section>
</template>

<style scoped lang="scss">
.notifications-preferences {
    .notifications-preferences-header {
        flex-grow: 1;
    }

    .notifications-preferences-description {
        margin-bottom: 1rem;
    }

    .notifications-preferences-body {
        display: flex;
        justify-content: space-around;

        .category-header {
            gap: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }

        .category-channel {
            display: flex;
            align-items: center;
        }
    }

    .push-notifications-notice {
        margin: 0.5rem auto;
        width: fit-content;
    }
}

.category-title {
    font-weight: bold;
}

.category-description {
    font-size: 0.8rem;
    font-style: italic;
    margin-bottom: 0.5rem;
}

.card-container {
    margin: 0.5rem;
}
</style>
