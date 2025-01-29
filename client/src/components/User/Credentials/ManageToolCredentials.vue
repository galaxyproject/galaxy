<script setup lang="ts">
import { ref } from "vue";

import type {
    CreateSourceCredentialsPayload,
    ServiceCredentialPayload,
    ServiceCredentialsDefinition,
    ServiceGroupPayload,
    SourceCredentialsDefinition,
    UserCredentials,
} from "@/api/users";
import { SECRET_PLACEHOLDER } from "@/stores/userCredentials";

import ServiceCredentials from "@/components/User/Credentials/ServiceCredentials.vue";

interface ManageToolCredentialsProps {
    toolId: string;
    toolVersion: string;
    toolCredentialsDefinition: SourceCredentialsDefinition;
    userToolCredentials?: UserCredentials[];
}

const props = withDefaults(defineProps<ManageToolCredentialsProps>(), {
    userToolCredentials: () => [],
});

const providedCredentials = ref<CreateSourceCredentialsPayload>(initializeCredentials());

const emit = defineEmits<{
    (e: "save-credentials", credentials: CreateSourceCredentialsPayload): void;
    (e: "delete-credentials-group", service_reference: string, groupName: string): void;
}>();

function saveCredentials() {
    emit("save-credentials", providedCredentials.value);
}

function initializeCredentials(): CreateSourceCredentialsPayload {
    const serviceCredentials = [];
    for (const service_reference of props.toolCredentialsDefinition.services.keys()) {
        const userProvidedCredentialForService = props.userToolCredentials.find(
            (c) => c.service_reference === service_reference
        );
        const currentGroup = userProvidedCredentialForService?.current_group_name ?? "default";
        const definition = getServiceCredentialsDefinition(service_reference);
        const groups = buildGroupsFromUserCredentials(definition, userProvidedCredentialForService);
        const credential: ServiceCredentialPayload = {
            service_reference: service_reference,
            current_group: currentGroup,
            groups,
        };
        serviceCredentials.push(credential);
    }

    const providedCredentials: CreateSourceCredentialsPayload = {
        source_type: "tool",
        source_id: props.toolId,
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
        (c) => c.service_reference === credential.service_reference
    );
    if (credentialFound) {
        credentialFound.groups.push(newSet);
    }
}

function onDeleteCredentialsGroup(service_reference: string, groupName: string) {
    const credentialFound = providedCredentials.value.credentials.find(
        (c) => c.service_reference === service_reference
    );
    if (credentialFound) {
        credentialFound.groups = credentialFound.groups.filter((g) => g.name !== groupName);
        emit("delete-credentials-group", service_reference, groupName);
    }
}

function onCurrentSetChange(credential: ServiceCredentialPayload, newSet: ServiceGroupPayload) {
    const credentialFound = providedCredentials.value.credentials.find(
        (c) => c.service_reference === credential.service_reference
    );
    if (credentialFound) {
        credentialFound.current_group = newSet.name;
    }
}

function getServiceCredentialsDefinition(service_reference: string): ServiceCredentialsDefinition {
    const definition = props.toolCredentialsDefinition.services.get(service_reference);
    if (!definition) {
        throw new Error(
            `No definition found for credential service reference ${service_reference} in tool ${props.toolId}`
        );
    }
    return definition;
}
</script>

<template>
    <div>
        <p>
            Here you can manage your credentials for the tool <strong>{{ toolId }}</strong> version
            <strong> {{ toolVersion }}</strong
            >. After you make any changes, don't forget to use the <i>Save Credentials</i> button to save them.
        </p>
        <ServiceCredentials
            v-for="credential in providedCredentials.credentials"
            :key="credential.service_reference"
            :credential-definition="getServiceCredentialsDefinition(credential.service_reference)"
            :credential-payload="credential"
            class="mb-2"
            @new-credentials-set="onNewCredentialsSet"
            @delete-credentials-group="onDeleteCredentialsGroup"
            @update-current-set="onCurrentSetChange" />
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
