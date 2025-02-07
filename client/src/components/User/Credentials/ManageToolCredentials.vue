<script setup lang="ts">
import { ref } from "vue";

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
import { SECRET_PLACEHOLDER } from "@/stores/userCredentials";

import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface ManageToolCredentialsProps {
    toolId: string;
    toolVersion: string;
    toolCredentialsDefinition: SourceCredentialsDefinition;
    toolUserCredentials?: UserCredentials[];
}

const props = withDefaults(defineProps<ManageToolCredentialsProps>(), {
    toolUserCredentials: () => [],
});

const providedCredentials = ref<CreateSourceCredentialsPayload>(initializeCredentials());

const emit = defineEmits<{
    (e: "save-credentials", credentials: CreateSourceCredentialsPayload): void;
    (e: "delete-credentials-group", serviceId: ServiceCredentialsIdentifier, groupName: string): void;
}>();

function saveCredentials() {
    emit("save-credentials", providedCredentials.value);
}

function initializeCredentials(): CreateSourceCredentialsPayload {
    const serviceCredentials = [];
    for (const key of props.toolCredentialsDefinition.services.keys()) {
        const userCredentialForService = getUserCredentialsForService(key);

        const currentGroup = userCredentialForService?.current_group_name ?? "default";
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

    const providedCredentials: CreateSourceCredentialsPayload = {
        source_type: "tool",
        source_id: props.toolId,
        source_version: props.toolVersion,
        credentials: serviceCredentials,
    };
    return providedCredentials;
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
    } else {
        const defaultGroup: ServiceGroupPayload = {
            name: "default",
            variables: definition.variables.map((variable) => ({
                name: variable.name,
                value: null,
            })),
            secrets: definition.secrets.map((secret) => ({
                name: secret.name,
                value: null,
            })),
        };
        groups.push(defaultGroup);
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

function onCurrentSetChange(credential: ServiceCredentialPayload, newSet: ServiceGroupPayload) {
    const credentialFound = providedCredentials.value.credentials.find(
        (c) => c.name === credential.name && c.version === credential.version
    );
    if (credentialFound) {
        credentialFound.current_group = newSet.name;
    }
}

function getServiceCredentialsDefinition(key: string): ServiceCredentialsDefinition {
    const definition = props.toolCredentialsDefinition.services.get(key);
    if (!definition) {
        throw new Error(`No definition found for credential service '${key}' in tool ${props.toolId}`);
    }
    return definition;
}

function getUserCredentialsForService(key: string): UserCredentials | undefined {
    return props.toolUserCredentials.find((c) => getKeyFromCredentialsIdentifier(c) === key);
}

function hasUserProvided(credential: ServiceCredentialPayload): boolean {
    return !!getUserCredentialsForService(getKeyFromCredentialsIdentifier(credential));
}
</script>

<template>
    <div>
        <p>
            Manage your credentials for <strong>{{ toolId }}</strong> (<strong>{{ toolVersion }}</strong
            >) here. After making any changes, be sure to click <strong>Save Credentials</strong> to apply them.
        </p>
        <div class="accordion">
            <ServiceCredentials
                v-for="credential in providedCredentials.credentials"
                :key="credential.name"
                :credential-definition="getServiceCredentialsDefinition(getKeyFromCredentialsIdentifier(credential))"
                :credential-payload="credential"
                :is-provided-by-user="hasUserProvided(credential)"
                class="mb-2"
                @new-credentials-set="onNewCredentialsSet"
                @delete-credentials-group="onDeleteCredentialsGroup"
                @update-current-set="onCurrentSetChange" />
        </div>

        <button class="btn-primary" @click="saveCredentials">Save Credentials</button>
    </div>
</template>

<style scoped>
.credential-card {
    border: 1px solid #ccc;
    padding: 1em;
    margin-bottom: 1em;
    border-radius: 5px;
}
.secret-input {
    display: flex;
    align-items: center;
}
.tick-icon {
    color: green;
    margin-left: 0.5em;
}
</style>
