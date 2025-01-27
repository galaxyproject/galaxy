<script setup lang="ts">
import { faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
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

const isAddingNewSet = ref(false);

const newSetName = ref<string>("");

const availableSets = computed<ServiceGroupPayload[]>(() => Object.values(props.credentialPayload.groups));

const canCreateNewSet = computed<boolean>(
    () => newSetName.value.trim() !== "" && !availableSets.value.some((set) => set.name === newSetName.value)
);

const canShowSetSelector = computed<boolean>(
    () => props.credentialDefinition.multiple && availableSets.value.length > 1
);

const canDeleteSet = computed<boolean>(() => selectedSet.value?.name !== "default");

const emit = defineEmits<{
    (e: "new-credentials-set", credential: ServiceCredentialPayload, newSet: ServiceGroupPayload): void;
    (e: "update-current-set", credential: ServiceCredentialPayload, newSet: ServiceGroupPayload): void;
    (e: "delete-credentials-group", service_reference: string, groupName: string): void;
}>();

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

function onDeleteGroup() {
    if (selectedSet.value) {
        //TODO: Implement confirmation dialog.
        const groupNameToDelete = selectedSet.value.name;
        const defaultSet = availableSets.value.find((set) => set.name === "default");
        if (defaultSet) {
            selectedSet.value = defaultSet;
            onCurrentSetChange(defaultSet);
        }
        emit("delete-credentials-group", props.credentialPayload.service_reference, groupNameToDelete);
    }
}
</script>

<template>
    <BCard>
        <form autocomplete="off">
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
                    title="You can provide multiple sets of credentials for this tool. But only one set can be active at a time.">
                    Multiple
                </BBadge>
            </h3>
            <p>{{ credentialDefinition.description }}</p>
            <div v-if="selectedSet">
                <div v-if="canShowSetSelector" class="set-selection-bar">
                    <b>Using set:</b>
                    <Multiselect
                        v-model="selectedSet"
                        :options="availableSets"
                        :allow-empty="false"
                        :show-labels="false"
                        :searchable="false"
                        track-by="name"
                        label="name"
                        @select="onCurrentSetChange" />
                    <button
                        v-if="canDeleteSet"
                        size="sm"
                        class="mx-2"
                        title="Delete this set of credentials."
                        @click="onDeleteGroup">
                        <FontAwesomeIcon :icon="faTrash" />
                    </button>
                </div>

                <div v-for="variable in selectedSet.variables" :key="variable.name">
                    <FormElement
                        :id="`${selectedSet.name}-${variable.name}-variable`"
                        v-model="variable.value"
                        type="text"
                        :title="getVariableTitle(variable.name, 'variable')"
                        :optional="credentialDefinition.optional"
                        :help="getVariableDescription(variable.name, 'variable')" />
                </div>
                <div v-for="secret in selectedSet.secrets" :key="secret.name" class="secret-input">
                    <FormElement
                        :id="`${selectedSet.name}-${secret.name}-secret`"
                        v-model="secret.value"
                        type="password"
                        :autocomplete="`${selectedSet.name}-${secret.name}-secret`"
                        :title="getVariableTitle(secret.name, 'secret')"
                        :optional="credentialDefinition.optional"
                        :help="getVariableDescription(secret.name, 'secret')" />
                </div>

                <div v-if="credentialDefinition.multiple" class="set-management-bar">
                    <button
                        v-if="!isAddingNewSet"
                        title="Create a new set for these credentials so you can choose between them."
                        @click="onAddingNewSet">
                        Create new set
                    </button>
                    <div v-else class="set-management-bar">
                        <FormElement
                            v-if="isAddingNewSet"
                            v-model="newSetName"
                            type="text"
                            placeholder="Enter new set name" />
                        <button
                            v-if="isAddingNewSet"
                            :disabled="!canCreateNewSet"
                            class="btn-primary"
                            @click="onCreateNewSet">
                            Confirm
                        </button>
                        <button v-if="isAddingNewSet" @click="onCancelAddingNewSet">Cancel</button>
                    </div>
                </div>
            </div>
        </form>
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
.set-management-bar {
    display: flex;
    gap: 1em;
    align-items: center;
}
.set-selection-bar {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 1em;
}
</style>
