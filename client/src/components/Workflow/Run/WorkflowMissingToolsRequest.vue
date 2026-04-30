<script setup lang="ts">
import { BAlert, BLink } from "bootstrap-vue";
import { computed, ref } from "vue";

import { submitUserNotification } from "@/api/notifications";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const props = defineProps<{
    missingToolIds: string[];
    workflowId: string;
}>();

const { config, isConfigLoaded } = useConfig();
const userStore = useUserStore();

const showConfirm = ref(false);
const submitting = ref(false);
const submittedNotificationId = ref<string | null>(null);
const errorMessage = ref("");

const showButton = computed(
    () =>
        isConfigLoaded.value &&
        config.value?.enable_tool_request_form &&
        !userStore.isAnonymous &&
        props.missingToolIds.length > 0,
);

const toolCount = computed(() => props.missingToolIds.length);

async function requestInstallation() {
    submitting.value = true;
    errorMessage.value = "";

    const toolVerb = toolCount.value === 1 ? "tool is" : "tools are";
    const description =
        `The following ${toolVerb} required by this workflow but not installed on this instance: ` +
        `${props.missingToolIds.join(", ")}. These tools are available in the Tool Shed and need to be installed.`;

    try {
        const notificationId = await submitUserNotification({
            tool_names: props.missingToolIds,
            workflow_id: props.workflowId,
            description,
        });

        submittedNotificationId.value = notificationId;
        showConfirm.value = false;
    } catch (e) {
        errorMessage.value = errorMessageAsString(e, "Failed to submit installation request. Please try again.");
    } finally {
        submitting.value = false;
    }
}
</script>

<template>
    <div v-if="showButton" class="workflow-missing-tools-request mt-3">
        <BAlert v-if="errorMessage" variant="danger" show dismissible @dismissed="errorMessage = ''">
            {{ errorMessage }}
        </BAlert>

        <BAlert v-if="submittedNotificationId" variant="success" show>
            Installation request sent &mdash;
            <BLink :href="`/user/notifications#notification-card-${submittedNotificationId}`">view your request</BLink>.
        </BAlert>

        <GButton
            v-else
            data-testid="request-install-btn"
            :disabled="submitting"
            variant="primary"
            size="small"
            @click="showConfirm = true">
            Request Installation ({{ toolCount }} missing {{ toolCount === 1 ? "tool" : "tools" }})
        </GButton>

        <GModal
            :show="showConfirm"
            title="Request Tool Installation"
            size="small"
            confirm
            ok-text="Send Request"
            :ok-disabled="submitting"
            :close-on-ok="false"
            @ok="requestInstallation"
            @cancel="showConfirm = false"
            @update:show="showConfirm = $event">
            <p>
                Request the admins to install
                <strong>{{ toolCount }} missing {{ toolCount === 1 ? "tool" : "tools" }}</strong>
                required by this workflow?
            </p>
            <p class="text-muted small mb-0">
                The admins will receive a notification and can install the tools from the Tool Shed.
            </p>
        </GModal>
    </div>
</template>
