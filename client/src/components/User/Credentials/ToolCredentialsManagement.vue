<script setup lang="ts">
import { BModal } from "bootstrap-vue";

import type { ServiceCredentialPayload, ServiceGroupPayload } from "@/api/users";
import { useUserToolCredentials } from "@/composables/userToolCredentials";

import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface Props {
    toolId: string;
    toolVersion: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "close"): void;
}>();

const { mutableUserCredentials, saveUserCredentials } = useUserToolCredentials(props.toolId, props.toolVersion);

function onSelectCredentials() {
    if (!mutableUserCredentials.value) {
        return;
    }

    saveUserCredentials(mutableUserCredentials.value);
}

function onNewCredentialsSet(credential: ServiceCredentialPayload, newSet: ServiceGroupPayload) {
    const credentialFound = mutableUserCredentials.value.credentials.find(
        (c) => c.name === credential.name && c.version === credential.version
    );

    if (credentialFound) {
        credentialFound.groups.push(newSet);
    }
}

function onCurrentSetChange(credential: ServiceCredentialPayload, newSet?: ServiceGroupPayload) {
    if (!newSet) {
        credential.current_group = null;
    } else {
        const credentialFound = mutableUserCredentials.value.credentials.find(
            (c) => c.name === credential.name && c.version === credential.version
        );
        if (credentialFound) {
            credentialFound.current_group = newSet.name;
        }
    }
}
</script>

<template>
    <BModal
        visible
        scrollable
        title="Select Credentials for this tool"
        no-close-on-backdrop
        no-close-on-esc
        button-size="md"
        size="lg"
        modal-class="manage-tool-credentials-modal"
        body-class="manage-tool-credentials-body"
        ok-title="Select Credentials"
        cancel-title="Close"
        cancel-variant="outline-danger"
        @ok="onSelectCredentials"
        @close="emit('close')">
        <p>
            Manage your credentials for <strong>{{ toolId }}</strong> (<strong>{{ toolVersion }}</strong
            >) here. After making any changes, select the credentials you want to use with this tool.
        </p>

        <div class="accordion">
            <ServiceCredentials
                v-for="credential in mutableUserCredentials.credentials"
                :key="credential.name"
                class="mb-2"
                :tool-id="props.toolId"
                :tool-version="props.toolVersion"
                :credential-payload="credential"
                @new-credentials-set="(newSet) => onNewCredentialsSet(credential, newSet)"
                @update-current-set="(updatedSet) => onCurrentSetChange(credential, updatedSet)" />
        </div>
    </BModal>
</template>

<style>
.manage-tool-credentials-body {
    height: 80vh;
}

.manage-tool-credentials-footer {
    display: flex;
    gap: 1em;
    justify-content: space-between;
}
</style>
