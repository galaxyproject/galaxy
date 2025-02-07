<script setup lang="ts">
import { faCaretRight, faPlus, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCollapse, BFormGroup } from "bootstrap-vue";
import { computed, ref } from "vue";
import Multiselect from "vue-multiselect";

import type {
    ServiceCredentialPayload,
    ServiceCredentialsDefinition,
    ServiceCredentialsIdentifier,
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

const isExpanded = ref(false);

const isAddingNewSet = ref(false);

const newSetName = ref<string>("");

const hasNameConflict = computed<boolean>(() => {
    return newSetName.value.trim() !== "" && availableSets.value.some((set) => set.name === newSetName.value);
});

const serviceName = computed<string>(() => props.credentialDefinition.label || props.credentialDefinition.name);

const availableSets = computed<ServiceGroupPayload[]>(() => Object.values(props.credentialPayload.groups));

const canCreateNewSet = computed<boolean>(
    () => newSetName.value.trim() !== "" && !availableSets.value.some((set) => set.name === newSetName.value)
);

const canDeleteSet = computed<boolean>(() => selectedSet.value?.name !== defaultSet.value?.name ?? false);

const defaultSet = computed<ServiceGroupPayload | undefined>(() =>
    availableSets.value.find((set) => set.name === "default")
);

const noCredentialsSet = computed<boolean>(() => {
    // TODO: Implement a real check for no credentials set.
    return availableSets.value.length === 0;
});

const emit = defineEmits<{
    (e: "new-credentials-set", credential: ServiceCredentialPayload, newSet: ServiceGroupPayload): void;
    (e: "update-current-set", credential: ServiceCredentialPayload, newSet: ServiceGroupPayload): void;
    (e: "delete-credentials-group", serviceId: ServiceCredentialsIdentifier, groupName: string): void;
}>();

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

function isVariableOptional(name: string, type: CredentialType): boolean {
    return getVariableDefinition(name, type).optional;
}

function onAddingNewSet() {
    isAddingNewSet.value = true;
}

function onCancelAddingNewSet() {
    isAddingNewSet.value = false;
    newSetName.value = "";
}

function onCreateNewSet() {
    const newSet: ServiceGroupPayload = {
        name: generateUniqueName(newSetName.value, props.credentialPayload.groups),
        variables: selectedSet.value?.variables.map((variable) => ({ ...variable, value: null })) || [],
        secrets: selectedSet.value?.secrets.map((secret) => ({ ...secret, value: null, alreadySet: false })) || [],
    };
    emit("new-credentials-set", props.credentialPayload, newSet);
    selectedSet.value = newSet;
    onCurrentSetChange(newSet);
    isAddingNewSet.value = false;
    newSetName.value = "";
}

function onCurrentSetChange(selectedSet: ServiceGroupPayload) {
    emit("update-current-set", props.credentialPayload, selectedSet);
}

function onDeleteSet() {
    if (selectedSet.value) {
        //TODO: Implement confirmation dialog.
        const groupNameToDelete = selectedSet.value.name;
        const defaultSet = availableSets.value.find((set) => set.name === "default");
        if (defaultSet) {
            selectedSet.value = defaultSet;
            onCurrentSetChange(defaultSet);
        }
        emit("delete-credentials-group", props.credentialPayload, groupNameToDelete);
    }
}
</script>

<template>
    <div>
        <div>
            <BButton class="service-title" block variant="outline-info" @click="isExpanded = !isExpanded">
                <span>
                    <FontAwesomeIcon v-if="!isExpanded" :icon="faCaretRight" />
                    <FontAwesomeIcon v-else :icon="faCaretRight" rotation="90" />
                    {{ serviceName }}
                </span>

                <span class="text-muted selected-set-info">
                    <span v-if="noCredentialsSet"> No credentials set</span>
                    <span v-else-if="selectedSet"> Using: {{ selectedSet.name }} </span>
                </span>
            </BButton>
        </div>
        <BCollapse :id="`accordion-${credentialDefinition.name}`" v-model="isExpanded" accordion="my-accordion">
            <div v-if="isAddingNewSet" class="credentials-form">
                <FormElement
                    v-model="newSetName"
                    type="text"
                    title="New set name"
                    :optional="false"
                    :help="`Enter a name for the new set of credentials for ${serviceName}`" />

                <div>
                    <BButton
                        variant="outline-info"
                        size="sm"
                        title="Create new set"
                        :disabled="!canCreateNewSet"
                        @click="onCreateNewSet">
                        Create
                    </BButton>
                    <BButton variant="outline-danger" size="sm" title="Cancel" @click="onCancelAddingNewSet">
                        Cancel
                    </BButton>

                    <span v-if="hasNameConflict" class="text-danger">
                        This name is already in use. Please choose another.
                    </span>
                </div>
            </div>
            <form v-else autocomplete="off" class="credentials-form">
                <p>{{ credentialDefinition.description }}</p>

                <div class="set-actions">
                    <BFormGroup
                        description="This is the current set of credentials you are using for this service. You can switch between sets or create a new one.">
                        <Multiselect
                            v-model="selectedSet"
                            :options="availableSets"
                            :label="`name`"
                            :track-by="`name`"
                            :allow-empty="false"
                            :show-labels="false"
                            :placeholder="`Select ${serviceName} set`"
                            @input="onCurrentSetChange" />
                    </BFormGroup>

                    <BButton
                        v-if="canDeleteSet"
                        variant="danger"
                        size="sm"
                        title="Delete selected set"
                        @click="onDeleteSet">
                        <FontAwesomeIcon :icon="faTrash" />
                    </BButton>
                    <BButton
                        variant="outline-info"
                        size="sm"
                        title="Create a new set of credentials"
                        @click="onAddingNewSet">
                        <FontAwesomeIcon :icon="faPlus" />
                    </BButton>
                </div>

                <div v-if="selectedSet" class="set-body">
                    <div v-for="variable in selectedSet.variables" :key="variable.name">
                        <FormElement
                            :id="`${selectedSet.name}-${variable.name}-variable`"
                            v-model="variable.value"
                            type="text"
                            :title="getVariableTitle(variable.name, 'variable')"
                            :optional="isVariableOptional(variable.name, 'variable')"
                            :help="getVariableDescription(variable.name, 'variable')" />
                    </div>
                    <div v-for="secret in selectedSet.secrets" :key="secret.name" class="secret-input">
                        <FormElement
                            :id="`${selectedSet.name}-${secret.name}-secret`"
                            v-model="secret.value"
                            type="password"
                            :autocomplete="`${selectedSet.name}-${secret.name}-secret`"
                            :title="getVariableTitle(secret.name, 'secret')"
                            :optional="isVariableOptional(secret.name, 'secret')"
                            :help="getVariableDescription(secret.name, 'secret')" />
                    </div>
                </div>
            </form>
        </BCollapse>
    </div>
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";

.service-title {
    font-size: 1rem;
    font-weight: bold;
    display: flex;
    justify-content: space-between;
    text-align: left;
}

.selected-set-info {
    font-size: 0.8rem;
    font-weight: normal;
    align-self: center;
}

.set-actions {
    display: flex;
    justify-content: space-between;

    button {
        margin-left: 0.5rem;
        align-self: baseline;
        padding: 9px;
    }
}

.set-body {
    border: 1px solid $gray-300;
    border-radius: 0.25rem;
    padding: 1rem;
}

.credentials-form {
    border-radius: 0 0 0.25rem 0.25rem;
    border: 1px solid $gray-300;
    border-top: none;
    padding: 1rem;
}
.secret-input {
    display: flex;
    align-items: center;
}
</style>
