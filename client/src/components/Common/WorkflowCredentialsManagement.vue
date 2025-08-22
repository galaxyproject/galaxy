<script setup lang="ts">
import { faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BModal } from "bootstrap-vue";
import { onMounted } from "vue";

import type { ServiceCredentialPayload, ServiceGroupPayload } from "@/api/users";
import { type ToolIdentifier, useUserMultiToolCredentials } from "@/composables/userMultiToolCredentials";
import { useToolStore } from "@/stores/toolStore";

import Heading from "@/components/Common/Heading.vue";
import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface Props {
    toolIdentifiers: ToolIdentifier[];
}

const props = defineProps<Props>();
const { getToolNameById } = useToolStore();

const { mutableUserCredentials, mutableUserCredentialsFor, checkAllUserCredentials, saveUserCredentials } =
    useUserMultiToolCredentials(props.toolIdentifiers);

const emit = defineEmits<{
    (e: "close"): void;
}>();

function onSelectCredentials() {
    if (!mutableUserCredentials.value) {
        return;
    }

    for (const ti of props.toolIdentifiers) {
        const credentials = mutableUserCredentialsFor.value(ti.toolId, ti.toolVersion);
        if (credentials) {
            saveUserCredentials(credentials);
        }
    }
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

onMounted(async () => {
    await checkAllUserCredentials();
});
</script>

<template>
    <BModal
        visible
        scrollable
        title="Select Credentials for this workflow"
        no-close-on-backdrop
        no-close-on-esc
        button-size="md"
        size="lg"
        modal-class="manage-workflow-credentials-modal"
        body-class="manage-workflow-credentials-body"
        ok-title="Select Credentials"
        cancel-title="Close"
        cancel-variant="outline-danger"
        @ok="onSelectCredentials"
        @close="emit('close')">
        <div v-for="(ti, i) in props.toolIdentifiers" :key="i" class="mb-2">
            <Heading inline h6 size="sm" class="mb-2" separator>
                <FontAwesomeIcon :icon="faWrench" fixed-width />
                {{ getToolNameById(ti.toolId) }} - ({{ ti.toolVersion }})
            </Heading>

            <div class="px-2">
                <ServiceCredentials
                    v-for="credential in mutableUserCredentialsFor(ti.toolId, ti.toolVersion).credentials"
                    :key="credential.name + credential.version"
                    class="mb-2"
                    :tool-id="ti.toolId"
                    :tool-version="ti.toolVersion"
                    :credential-payload="credential"
                    @new-credentials-set="(newSet) => onNewCredentialsSet(credential, newSet)"
                    @update-current-set="(updatedSet) => onCurrentSetChange(credential, updatedSet)">
                </ServiceCredentials>
            </div>
        </div>
    </BModal>
</template>

<style>
.manage-workflow-credentials-body {
    height: 80vh;
}
</style>
