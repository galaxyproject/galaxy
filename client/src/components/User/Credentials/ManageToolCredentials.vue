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
}>();

function saveCredentials() {
    emit("save-credentials", providedCredentials.value);
}

function initializeCredentials(): CreateSourceCredentialsPayload {
    const serviceCredentials = [];
    for (const reference of props.toolCredentialsDefinition.services.keys()) {
        const userProvidedCredentialForService = props.userToolCredentials.find((c) => c.reference === reference);
        const currentGroup = userProvidedCredentialForService?.current_group_name ?? "default";
        const definition = getServiceCredentialsDefinition(reference);
        const groups = buildGroupsFromUserCredentials(definition, userProvidedCredentialForService);
        const credential: ServiceCredentialPayload = {
            reference,
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
                variables: group.variables,
                secrets: group.secrets.map((secret) => ({
                    name: secret.name,
                    value: null,
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
    const credentialFound = providedCredentials.value.credentials.find((c) => c.reference === credential.reference);
    if (credentialFound) {
        credentialFound.groups.push(newSet);
    }
}

function onCurrentSetChange(credential: ServiceCredentialPayload, newSet: ServiceGroupPayload) {
    const credentialFound = providedCredentials.value.credentials.find((c) => c.reference === credential.reference);
    if (credentialFound) {
        credentialFound.current_group = newSet.name;
    }
}

function getServiceCredentialsDefinition(reference: string): ServiceCredentialsDefinition {
    const definition = props.toolCredentialsDefinition.services.get(reference);
    if (!definition) {
        throw new Error(`No definition found for credential reference ${reference} in tool ${props.toolId}`);
    }
    return definition;
}
</script>

<template>
    <div>
        <p>
            Here you can manage your credentials for the tool <strong>{{ toolId }}</strong> version
            <strong> {{ toolVersion }}</strong
            >.
        </p>
        <ServiceCredentials
            v-for="credential in providedCredentials.credentials"
            :key="credential.reference"
            :credential-definition="getServiceCredentialsDefinition(credential.reference)"
            :credential-payload="credential"
            @new-credentials-set="onNewCredentialsSet"
            @update-current-set="onCurrentSetChange" />
        <button @click="saveCredentials">Save Credentials</button>
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
