<script setup lang="ts">
import { BModal } from "bootstrap-vue";
import { computed, onMounted } from "vue";

import type {
    CreateSourceCredentialsPayload,
    ServiceCredentialPayload,
    ServiceCredentialsIdentifier,
    ServiceGroupPayload,
    UserCredentials,
} from "@/api/users";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useToolCredentialsDefinitionsStore } from "@/stores/toolCredentialsDefinitionsStore";

import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface ManageToolCredentialsProps {
    toolId: string;
    toolVersion: string;
}

const props = defineProps<ManageToolCredentialsProps>();

const emit = defineEmits<{
    (e: "onUpdateCredentialsList", data?: UserCredentials[]): void;
    (e: "save-credentials", credentials: CreateSourceCredentialsPayload): void;
    (e: "delete-credentials-group", serviceId: ServiceCredentialsIdentifier, groupName: string): void;
    (e: "close"): void;
}>();

const { getServiceCredentialsDefinition } = useToolCredentialsDefinitionsStore();
const { checkUserCredentials, mutableUserCredentials } = useUserToolCredentials(props.toolId, props.toolVersion);

const serviceCredentialsDefinition = computed(
    () => (credentialPayload: ServiceCredentialPayload) =>
        getServiceCredentialsDefinition(props.toolId, props.toolVersion, credentialPayload)
);

function saveCredentials() {
    if (!mutableUserCredentials.value) {
        return;
    }

    emit("save-credentials", mutableUserCredentials.value);
}

function onNewCredentialsSet(credential: ServiceCredentialPayload, newSet: ServiceGroupPayload) {
    const credentialFound = mutableUserCredentials.value.credentials.find(
        (c) => c.name === credential.name && c.version === credential.version
    );

    if (credentialFound) {
        credentialFound.groups.push(newSet);
    }
}

function onDeleteCredentialsGroup(serviceId: ServiceCredentialsIdentifier, groupName: string) {
    const credentialFound = mutableUserCredentials.value.credentials.find(
        (c) => c.name === serviceId.name && c.version === serviceId.version
    );

    if (credentialFound) {
        credentialFound.groups = credentialFound.groups.filter((g) => g.name !== groupName);
        emit("delete-credentials-group", serviceId, groupName);
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

function onUpdateCredentialsList(data?: UserCredentials[]) {
    emit("onUpdateCredentialsList", data);
}

onMounted(async () => {
    await checkUserCredentials();
});
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
        @ok="saveCredentials"
        @close="emit('close')">
        <p>
            Manage your credentials for <strong>{{ toolId }}</strong> (<strong>{{ toolVersion }}</strong
            >) here. After making any changes, select the credentials you want to use with this tool.
        </p>

        <div class="accordion">
            <template v-for="credential in mutableUserCredentials.credentials">
                <ServiceCredentials
                    v-if="serviceCredentialsDefinition(credential)"
                    :key="credential.name"
                    class="mb-2"
                    :tool-id="props.toolId"
                    :tool-version="props.toolVersion"
                    :credential-payload="credential"
                    :service-credentials-definition="serviceCredentialsDefinition(credential)"
                    @update-credentials-list="onUpdateCredentialsList"
                    @new-credentials-set="(newSet) => onNewCredentialsSet(credential, newSet)"
                    @delete-credentials-group="onDeleteCredentialsGroup"
                    @update-current-set="(updatedSet) => onCurrentSetChange(credential, updatedSet)" />
            </template>
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
