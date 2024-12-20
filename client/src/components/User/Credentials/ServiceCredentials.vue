<script setup lang="ts">
import { BBadge, BCard } from "bootstrap-vue";
import { computed, ref } from "vue";
import Multiselect from "vue-multiselect";

import type {
    ServiceCredentialPayload,
    ServiceCredentialsDefinition,
    ServiceGroupPayload,
    ServiceVariableDefinition,
} from "@/api/users";

import FormElement from "@/components/Form/FormElement.vue";

type CredentialType = "variable" | "secret";

interface Props {
    credentialDefinition: ServiceCredentialsDefinition;
    credentialPayload: ServiceCredentialPayload;
}

const props = defineProps<Props>();

const selectedSet = ref<ServiceGroupPayload | undefined>(
    props.credentialPayload.groups.find((group) => group.name === props.credentialPayload.current_group)
);
const availableSets = computed<ServiceGroupPayload[]>(() => Object.values(props.credentialPayload.groups));
const newSetName = ref<string>("");
const canCreateNewSet = computed<boolean>(() => newSetName.value.trim() !== "");

const emit = defineEmits<{
    (e: "new-credentials-set", credential: ServiceCredentialPayload, newSet: ServiceGroupPayload): void;
    (e: "update-current-set", credential: ServiceCredentialPayload, newSet: ServiceGroupPayload): void;
}>();

function onCreateNewSet() {
    const newSet: ServiceGroupPayload = {
        name: generateUniqueName(newSetName.value, props.credentialPayload.groups),
        variables: selectedSet.value?.variables.map((variable) => ({ ...variable, value: null })) || [],
        secrets: selectedSet.value?.secrets.map((secret) => ({ ...secret, value: null, alreadySet: false })) || [],
    };
    emit("new-credentials-set", props.credentialPayload, newSet);
    selectedSet.value = newSet;
}

function onCurrentSetChange(selectedSet: ServiceGroupPayload) {
    emit("update-current-set", props.credentialPayload, selectedSet);
}

function generateUniqueName(template: string, sets: ServiceGroupPayload[]): string {
    let name = template;
    let counter = 1;
    while (sets.some((set) => set.name === name)) {
        name = `${template} ${counter}`;
        counter++;
    }
    return name;
}

function getVariableDefinition(name: string, type: CredentialType): ServiceVariableDefinition {
    const definition = props.credentialDefinition[type === "variable" ? "variables" : "secrets"].find(
        (variable) => variable.name === name
    );
    if (!definition) {
        throw new Error(`Variable definition not found for variable ${name}`);
    }
    return definition;
}

function getVariableTitle(name: string, type: CredentialType): string {
    return getVariableDefinition(name, type).label || name;
}

function getVariableDescription(name: string, type: CredentialType): string | undefined {
    return getVariableDefinition(name, type).description;
}
</script>

<template>
    <BCard>
        <h3>
            {{ credentialDefinition.label || credentialDefinition.name }}
            <BBadge
                v-if="credentialDefinition.optional"
                variant="secondary"
                class="optional-credentials"
                title="These credentials are optional. If you do not provide them, the tool will use default values or
                    anonymous access.">
                Optional
            </BBadge>
            <BBadge
                v-else
                variant="danger"
                class="required-credentials"
                title="These credentials are required. You must provide them to use the tool.">
                Required
            </BBadge>
            <BBadge
                v-if="credentialDefinition.multiple"
                variant="info"
                title="You can provide multiple sets of credentials for this tool.">
                Multiple
            </BBadge>
        </h3>
        <p>{{ credentialDefinition.description }}</p>
        <div v-if="selectedSet">
            <h4 v-if="credentialDefinition.multiple">
                Select a set of credentials:
                <Multiselect
                    v-model="selectedSet"
                    :options="availableSets"
                    :allow-empty="false"
                    :show-labels="false"
                    track-by="name"
                    label="name"
                    @select="onCurrentSetChange" />

                <label for="newSetName">Or create new set:</label>
                <input id="newSetName" v-model="newSetName" type="text" placeholder="New set name" />
                <button :disabled="!canCreateNewSet" @click="onCreateNewSet">Create</button>
            </h4>

            <div v-for="variable in selectedSet.variables" :key="variable.name">
                <!-- TODO Use new component here? -->
                <FormElement
                    :id="variable.name"
                    v-model="variable.name"
                    type="text"
                    :title="getVariableTitle(variable.name, 'variable')"
                    :optional="credentialDefinition.optional"
                    :help="getVariableDescription(variable.name, 'variable')" />
            </div>
            <div v-for="secret in selectedSet.secrets" :key="secret.name" class="secret-input">
                <!-- TODO Use VaultSecret component here or similar? -->
                <FormElement
                    :id="secret.name"
                    v-model="secret.name"
                    type="password"
                    :title="getVariableTitle(secret.name, 'secret')"
                    :optional="credentialDefinition.optional"
                    :help="getVariableDescription(secret.name, 'secret')" />
            </div>
        </div>
    </BCard>
</template>

<style scoped>
.secret-input {
    display: flex;
    align-items: center;
}
.tick-icon {
    color: green;
    margin-left: 0.5em;
}
</style>
