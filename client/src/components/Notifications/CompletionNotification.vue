<script setup lang="ts">
import { faBell, faBellSlash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import type { UserNotificationPreferences } from "@/api/notifications";
import { useConfig } from "@/composables/config";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

const props = withDefaults(defineProps<{ value: boolean; kind?: "workflow" | "tool" }>(), { kind: "workflow" });
const emit = defineEmits<{
    (e: "input", value: boolean): void;
    (e: "busy", value: boolean): void;
}>();
const { config, isConfigLoaded } = useConfig();
const enabled = computed(() => isConfigLoaded.value && config.value.enable_notification_system);
const category = computed(() => (props.kind === "tool" ? "tool_execution_completed" : "workflow_execution_completed"));
const buttonLabel = computed(() => `Completion notifications: ${props.value ? "on" : "off"} for this run`);
const trigger = ref<InstanceType<typeof GButton>>();
const settings = ref<UserNotificationPreferences["workflow_execution_completed"]>();
const emailSupported = ref(false);
const pendingEmail = ref<boolean>();
const busy = ref(false);
const errorMessage = ref<string | null>(null);

function setBusy(value: boolean) {
    busy.value = value;
    emit("busy", value);
}

async function loadPreferences() {
    setBusy(true);
    errorMessage.value = null;
    try {
        const { data, error, response } = await GalaxyApi().GET("/api/notifications/preferences");
        if (error) {
            throw error;
        }
        settings.value = data.preferences[category.value];
        emailSupported.value = response.headers.get("supported-channels")?.split(",").includes("email") ?? false;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        setBusy(false);
    }
}

async function saveEmailPreference(email: boolean) {
    if (!settings.value || busy.value) {
        return;
    }
    pendingEmail.value = email;
    setBusy(true);
    errorMessage.value = null;
    try {
        const { data, error } = await GalaxyApi().PUT("/api/notifications/preferences", {
            body: {
                preferences: {
                    [category.value]: {
                        ...settings.value,
                        channels: { ...settings.value.channels, email },
                    },
                },
            },
        });
        if (error) {
            throw error;
        }
        settings.value = data.preferences[category.value];
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        pendingEmail.value = undefined;
        setBusy(false);
    }
}

watch(enabled, (value) => {
    if (!value) {
        emit("input", false);
    }
});
</script>

<template>
    <span v-if="enabled" class="d-inline-flex align-items-center" data-test-id="completion-notification">
        <GButton
            ref="trigger"
            size="small"
            transparent
            color="blue"
            :title="buttonLabel"
            :aria-label="buttonLabel"
            data-test-id="completion-notification-button">
            <FontAwesomeIcon :icon="props.value ? faBell : faBellSlash" fixed-width />
        </GButton>
        <GPopover
            :target="() => trigger"
            triggers="click"
            placement="bottomright"
            title="Completion notifications"
            custom-class="completion-notification-popover"
            @shown="loadPreferences">
            <div class="completion-notification-settings">
                <h3 class="h6">This run</h3>
                <GCheckbox
                    :model-value="props.value"
                    data-test-id="send-notification-checkbox"
                    @update:model-value="emit('input', $event)">
                    Notify me
                </GCheckbox>
                <p class="text-muted mt-1 mb-3">For this run only.</p>
                <h3 class="h6">Delivery settings</h3>
                <p v-if="busy && !settings" role="status">Loading delivery settings…</p>
                <GCheckbox
                    v-if="emailSupported"
                    :model-value="pendingEmail ?? settings?.channels.email ?? false"
                    :disabled="busy || !settings"
                    data-test-id="completion-email-checkbox"
                    @update:model-value="saveEmailPreference($event)">
                    Send email
                </GCheckbox>
                <p v-if="emailSupported" class="text-muted mt-1">Saved for future and active {{ props.kind }} runs.</p>
                <p v-else-if="settings" class="text-muted">Email delivery is not available on this server.</p>
                <GAlert v-if="settings && !settings.enabled" variant="warning">
                    {{ props.kind === "tool" ? "Tool" : "Workflow" }} notifications are off in your account. Enable them
                    in notification settings.
                </GAlert>
                <GAlert v-if="errorMessage" variant="warning">
                    Could not load or save settings: {{ errorMessage }}
                    <GButton v-if="!settings" size="small" :disabled="busy" @click="loadPreferences">Retry</GButton>
                </GAlert>
                <a
                    :href="prependPath('/user/notifications/preferences')"
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="All notification settings (opens in a new tab)">
                    All notification settings
                </a>
            </div>
        </GPopover>
    </span>
</template>

<style scoped>
:global(.completion-notification-popover) {
    max-width: calc(100vw - 1rem);
}

.completion-notification-settings {
    width: 18rem;
    max-width: calc(100vw - 3rem);
}
</style>
