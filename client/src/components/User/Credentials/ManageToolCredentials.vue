<script setup lang="ts">
import { BModal } from "bootstrap-vue";
import { computed, onMounted } from "vue";

import {
    type CreateSourceCredentialsPayload,
    getKeyFromCredentialsIdentifier,
    type ServiceCredentialPayload,
    type ServiceCredentialsDefinition,
    type ServiceCredentialsIdentifier,
    type ServiceGroupPayload,
    type SourceCredentialsDefinition,
    type UserCredentials,
} from "@/api/users";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { SECRET_PLACEHOLDER } from "@/stores/userCredentials";

import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface ManageToolCredentialsProps {
    toolId: string;
    toolVersion: string;
    toolCredentialsDefinition: ServiceCredentialsDefinition[];
    sourceCredentialsDefinition: SourceCredentialsDefinition;
}

const props = defineProps<ManageToolCredentialsProps>();

const emit = defineEmits<{
    (e: "onUpdateCredentialsList", data?: UserCredentials[]): void;
    (e: "save-credentials", credentials: CreateSourceCredentialsPayload): void;
    (e: "delete-credentials-group", serviceId: ServiceCredentialsIdentifier, groupName: string): void;
    (e: "close"): void;
}>();

const sourceData = computed<{
    sourceId: string;
    sourceType: "tool";
    sourceVersion: string;
}>(() => ({
    sourceId: props.toolId,
    sourceType: "tool",
    sourceVersion: props.toolVersion,
}));

const providedCredentials = computed<CreateSourceCredentialsPayload>(() => {
    return initializeCredentials();
});

function saveCredentials() {
    if (!providedCredentials.value) {
        return;
    }

    emit("save-credentials", providedCredentials.value);
}

function initializeCredentials(): CreateSourceCredentialsPayload {
    const serviceCredentials = [];
    for (const key of props.sourceCredentialsDefinition.services.keys()) {
        const userCredentialForService = getUserCredentialsForService(key);

        const currentGroup = userCredentialForService?.current_group_name;
        const definition = getServiceCredentialsDefinition(key);
        const groups = buildGroupsFromUserCredentials(definition, userCredentialForService);
        const credential: ServiceCredentialPayload = {
            name: definition.name,
            version: definition.version,
            current_group: currentGroup,
            groups,
        };
        serviceCredentials.push(credential);
    }

    return {
        source_type: "tool",
        source_id: props.toolId,
        source_version: props.toolVersion,
        credentials: serviceCredentials,
    };
}

function buildGroupsFromUserCredentials(
    definition: ServiceCredentialsDefinition,
    userCredentials?: UserCredentials
): ServiceGroupPayload[] {
    const groups: ServiceGroupPayload[] = [];
    if (userCredentials) {
        const existingGroups = Object.values(userCredentials.groups);
        for (const group of existingGroups) {
            const newGroup: ServiceGroupPayload = {
                name: group.name,
                variables: definition.variables.map((variable) => ({
                    name: variable.name,
                    value: group.variables.find((v) => v.name === variable.name)?.value ?? null,
                })),
                secrets: definition.secrets.map((secret) => ({
                    name: secret.name,
                    value: group.secrets.find((s) => s.name === secret.name)?.is_set ? SECRET_PLACEHOLDER : null,
                    alreadySet: group.secrets.find((s) => s.name === secret.name)?.is_set ?? false,
                })),
            };
            groups.push(newGroup);
        }
    }
    return groups;
}

function onNewCredentialsSet(credential: ServiceCredentialPayload, newSet: ServiceGroupPayload) {
    const credentialFound = providedCredentials.value.credentials.find(
        (c) => c.name === credential.name && c.version === credential.version
    );

    if (credentialFound) {
        credentialFound.groups.push(newSet);
    }
}

function onDeleteCredentialsGroup(serviceId: ServiceCredentialsIdentifier, groupName: string) {
    const credentialFound = providedCredentials.value.credentials.find(
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
        const credentialFound = providedCredentials.value.credentials.find(
            (c) => c.name === credential.name && c.version === credential.version
        );
        if (credentialFound) {
            credentialFound.current_group = newSet.name;
        }
    }
}

function getServiceCredentialsDefinition(key: string): ServiceCredentialsDefinition {
    const definition = props.sourceCredentialsDefinition.services.get(key);
    if (!definition) {
        throw new Error(`No definition found for credential service '${key}' in tool ${props.toolId}`);
    }
    return definition;
}

const { userCredentials, checkUserCredentials } = useUserToolCredentials(
    props.toolId,
    props.toolVersion,
    props.toolCredentialsDefinition
);

function getUserCredentialsForService(key: string): UserCredentials | undefined {
    return userCredentials.value?.find((c) => getKeyFromCredentialsIdentifier(c) === key);
}

function hasUserProvided(credential: ServiceCredentialPayload): boolean {
    return !!getUserCredentialsForService(getKeyFromCredentialsIdentifier(credential));
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
            <ServiceCredentials
                v-for="credential in providedCredentials.credentials"
                :key="credential.name"
                :source-data="sourceData"
                :credential-definition="getServiceCredentialsDefinition(getKeyFromCredentialsIdentifier(credential))"
                :credential-payload="credential"
                :is-provided-by-user="hasUserProvided(credential)"
                class="mb-2"
                @update-credentials-list="onUpdateCredentialsList"
                @new-credentials-set="(newSet) => onNewCredentialsSet(credential, newSet)"
                @delete-credentials-group="onDeleteCredentialsGroup"
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
