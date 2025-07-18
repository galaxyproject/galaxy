<script setup lang="ts">
import { faBan, faCaretRight, faCheck, faPlus, faSave, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCollapse, BFormInput } from "bootstrap-vue";
import { faPencil, faSpinner, faX, faXmark } from "font-awesome-6";
import { computed, ref } from "vue";

import type {
    ServiceCredentialPayload,
    ServiceCredentialsDefinition,
    ServiceCredentialsIdentifier,
    ServiceGroupPayload,
    ServiceVariableDefinition,
    UserCredentials,
} from "@/api/users";
import type { CardAction, CardIndicator } from "@/components/Common/GCard.types";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useUserCredentialsStore } from "@/stores/userCredentials";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";

type CredentialType = "variable" | "secret";

interface Props {
    credentialDefinition: ServiceCredentialsDefinition;
    credentialPayload: ServiceCredentialPayload;
    isProvidedByUser: boolean;
    sourceData: {
        sourceId: string;
        sourceType: "tool";
        sourceVersion: string;
    };
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update-credentials-list", userCredentials?: UserCredentials[]): void;
    (e: "new-credentials-set", credential: ServiceCredentialPayload, newSet: ServiceGroupPayload): void;
    (e: "update-current-set", credential: ServiceCredentialPayload, newSet?: ServiceGroupPayload): void;
    (e: "delete-credentials-group", serviceId: ServiceCredentialsIdentifier, groupName: string): void;
}>();

const { confirm } = useConfirmDialog();

const userCredentialsStore = useUserCredentialsStore();

const isBusy = ref(false);
const saveButtonText = ref("Save");
const isNewSet = ref(false);

const selectedSet = computed<ServiceGroupPayload | undefined>(() =>
    props.credentialPayload.groups.find((group) => group.name === props.credentialPayload.current_group)
);

const isExpanded = ref(false);

const newNameError = ref<string | undefined>(undefined);

const setNameHelp = computed<string>(() => {
    // if (selectedSet.value?.name === defaultSet.value?.name) {
    //     return "The default set cannot be renamed.";
    // }

    return `Enter a name for the set of credentials for ${serviceName.value}`;
});

// const hasNameConflict = computed<boolean>(() => {
//     return newSetName.value.trim() !== "" && availableSets.value.some((set) => set.name === newSetName.value);
// });

const serviceName = computed<string>(() => props.credentialDefinition.label || props.credentialDefinition.name);

const availableSets = computed<ServiceGroupPayload[]>(() => Object.values(props.credentialPayload.groups));

const canCreateNewSet = computed<boolean>(
    () =>
        selectedSet.value?.name.trim() !== "" &&
        !availableSets.value.some((set) => set.name === selectedSet.value?.name)
);

const canDeleteSet = computed<boolean>(() => selectedSet.value?.name !== defaultSet.value?.name);

const defaultSet = computed<ServiceGroupPayload | undefined>(() =>
    availableSets.value.find((set) => set.name === "default")
);

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

function onCreateNewSet() {
    console.log("Creating new set of credentials");
    const newSet: ServiceGroupPayload = {
        name: generateUniqueName("new credential", props.credentialPayload.groups),
        variables: selectedSet.value?.variables.map((variable) => ({ ...variable, value: null })) || [],
        secrets: selectedSet.value?.secrets.map((secret) => ({ ...secret, value: null, alreadySet: false })) || [],
    };

    console.log("New set created:", newSet);

    emit("new-credentials-set", props.credentialPayload, newSet);
    // tmpSet.value = newSet;
    onCurrentSetChange(newSet);
    console.log("New set emitted:", newSet);

    isNewSet.value = true;

    // toggleEditingMode()
}

function onCurrentSetChange(selectedSet?: ServiceGroupPayload) {
    emit("update-current-set", props.credentialPayload, selectedSet);
}

const editMode = ref<Record<string, boolean>>({});

function toggleEditingMode(setName: string, state?: boolean) {
    editMode.value = {
        ...editMode.value,
        [setName]: state !== undefined ? state : !editMode.value[setName],
    };

    if (!state) {
        // tmpSet.value = undefined;
        isNewSet.value = false;
    }
}

async function onDeleteSet() {
    const confirmed = await confirm("Are you sure you want to delete this set of credentials?", {
        title: "Delete credentials set",
        okTitle: "Delete set",
        okVariant: "danger",
        cancelVariant: "outline-primary",
    });

    if (confirmed && selectedSet.value) {
        const groupNameToDelete = selectedSet.value?.name;
        const defaultSet = availableSets.value.find((set) => set.name === "default");

        if (defaultSet) {
            // selectedSet.value = defaultSet;
            onCurrentSetChange(defaultSet);
        }

        emit("delete-credentials-group", props.credentialPayload, groupNameToDelete);
    }
}

function onDiscardSet(setName: string) {
    // selectedSet.value = availableSets.value.find((set) => set.name === props.credentialPayload.current_group);
    toggleEditingMode(setName, false);
}

const editSet = ref<Record<string, { data: ServiceGroupPayload }>>({});

function onEditSet(setName: string) {
    // tmpSet.value = undefined;
    // tmpSet.value = { ...selectedSet.value! };
    // originalName.value = tmpSet.value!.name;

    isNewSet.value = false;

    editSet.value = {
        ...editSet.value,
        [setName]: { data: { ...availableSets.value.find((set) => set.name === setName)! } },
    };

    toggleEditingMode(setName);
}

async function onSaveSet(setName: string) {
    // if (newNameError.value) {
    //     return;
    // }

    // if (selectedSet.value) {
    //     emit("update-current-set", props.credentialPayload, selectedSet.value);
    // }

    // toggleEditingMode(false);

    saveButtonText.value = "Saving";
    // tmpSet

    try {
        isBusy.value = true;

        if (!editSet.value[setName]) {
            return;
        }

        const toSend = {
            source_id: props.sourceData.sourceId,
            source_type: props.sourceData.sourceType,
            source_version: props.sourceData.sourceVersion,
            credentials: [{ ...props.credentialPayload, groups: [editSet.value[setName].data] }],
        };

        const newData = await userCredentialsStore.saveUserCredentialsForTool(toSend);

        emit("update-credentials-list", newData);
        // toggleEditingMode(tmpSet.value!.name, false);
        toggleEditingMode(setName, false);
    } catch (error) {
        // TODO: Implement error handling.
        console.error("Error saving user credentials", error);
    } finally {
        isBusy.value = false;
        saveButtonText.value = "Save";
    }
}

function disableSaveButton(setName: string): boolean {
    if (!editSet.value[setName]) {
        return true;
    }

    const data = editSet.value[setName].data;

    return (
        isBusy.value ||
        !data.name ||
        data.variables.some((variable) => !variable.value && !isVariableOptional(variable.name, "variable")) ||
        data.secrets.some((secret) => !secret.value && !isVariableOptional(secret.name, "secret")) ||
        data.name === defaultSet.value?.name ||
        availableSets.value.some((set) => set.name === data.name)
    );
}

function primaryActions(setData: ServiceGroupPayload): CardAction[] {
    return [
        {
            id: `delete-${setData.name}`,
            label: "",
            title: "Delete this set",
            icon: faTrash,
            variant: "outline-danger",
            handler: onDeleteSet,
            visible:
                setData?.name !== defaultSet.value?.name &&
                setData.name !== selectedSet.value?.name &&
                editMode.value[setData.name] !== true,
        },
        {
            id: `edit-${setData.name}`,
            label: "Edit",
            title: "Edit this set",
            icon: faPencil,
            variant: "outline-info",
            handler: () => onEditSet(setData.name),
            visible: editMode.value[setData.name] !== true,
        },
        {
            id: `use-${setData.name}`,
            label: selectedSet.value?.name === setData.name ? "This set is currently used" : "Use this set",
            title: "Use this set",
            icon: selectedSet.value?.name === setData.name ? faX : faCheck,
            variant: "outline-info",
            handler: () => onCurrentSetChange(setData),
            disabled: selectedSet.value?.name === setData.name,
            visible: editMode.value[setData.name] !== true && selectedSet.value?.name !== setData.name,
        },
        {
            id: `discard-${setData.name}`,
            label: "Discard",
            title: "Discard changes to this set",
            icon: faBan,
            variant: "outline-danger",
            handler: () => onDiscardSet(setData.name),
            disabled: isBusy.value,
            visible: editMode.value[setData.name] === true,
        },
        {
            id: `save-${setData.name}`,
            label: "Save",
            title: "Save changes to this set",
            icon: isBusy.value ? faSpinner : faSave,
            variant: "outline-info",
            handler: () => onSaveSet(setData.name),
            disabled: disableSaveButton(setData.name),
            visible: editMode.value[setData.name] === true,
        },
    ];
}

function setIndicators(setName: string): CardIndicator[] {
    return [
        {
            id: "current-set",
            label: "",
            title: "This set will be used for this tool in the workflow",
            icon: faCheck,
            visible: selectedSet.value?.name === setName,
        },
    ];
}

function onClearSelection() {
    onCurrentSetChange(undefined);
}

function onNameInput(setName: string, value?: string) {
    if (!availableSets.value.some((set) => set.name === value)) {
        if (editSet.value[setName]) {
            editSet.value = {
                ...editSet.value,
                [setName]: { data: { ...editSet.value[setName].data, name: value?.trim() || "" } },
            };
            newNameError.value = undefined;
        }
    } else {
        newNameError.value = "This name is not allowed.";
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
                    <span v-if="isProvidedByUser && selectedSet">
                        Using: <b>{{ selectedSet?.name }}</b>
                    </span>
                    <span v-else> No credentials set</span>
                </span>
            </BButton>
        </div>

        <BCollapse :id="`accordion-${credentialDefinition.name}`" v-model="isExpanded" class="px-2">
            <div class="d-flex flex-column align-items-center mt-2">
                <span class="text-md">{{ credentialDefinition.description }}</span>

                <GCard
                    v-for="avs in availableSets"
                    :key="avs.name"
                    :title="avs.name"
                    :selected="selectedSet?.name === avs.name"
                    :indicators="setIndicators(avs.name)"
                    :primary-actions="primaryActions(avs)">
                    <template v-if="editMode[avs.name] && editSet[avs.name]" v-slot:description>
                        <div class="p-2">
                            Editing set of credentials for <b>{{ avs.name }}</b>

                            <BFormInput
                                v-if="editSet[avs.name]?.data.name !== defaultSet?.name"
                                :value="editSet[avs.name]?.data.name"
                                type="text"
                                :state="editSet[avs.name]?.data.name ? true : false"
                                :placeholder="setNameHelp"
                                :title="setNameHelp"
                                :aria-label="setNameHelp"
                                class="mb-2"
                                @input="(newValue) => onNameInput(avs.name, newValue)" />

                            <div v-for="variable in editSet[avs.name]?.data.variables" :key="variable.name">
                                <label :for="`${editSet[avs.name]?.data.name}-${variable.name}-variable`">
                                    {{ getVariableTitle(variable.name, "variable") }}
                                </label>
                                <BFormInput
                                    :id="`${editSet[avs.name]?.data.name}-${variable.name}-variable`"
                                    v-model="variable.value"
                                    type="text"
                                    :state="
                                        !variable.value
                                            ? isVariableOptional(variable.name, 'variable')
                                                ? null
                                                : false
                                            : true
                                    "
                                    :placeholder="getVariableTitle(variable.name, 'variable')"
                                    :title="getVariableTitle(variable.name, 'variable')"
                                    :aria-label="getVariableTitle(variable.name, 'variable')"
                                    :required="!isVariableOptional(variable.name, 'variable')"
                                    :readonly="false"
                                    class="mb-2" />
                            </div>

                            <div v-for="secret in editSet[avs.name]?.data.secrets" :key="secret.name">
                                <label :for="`${editSet[avs.name]?.data.name}-${secret.name}-secret`">
                                    {{ getVariableTitle(secret.name, "secret") }}
                                </label>
                                <BFormInput
                                    :id="`${editSet[avs.name]?.data.name}-${secret.name}-secret`"
                                    v-model="secret.value"
                                    type="password"
                                    :autocomplete="`${editSet[avs.name]?.data.name}-${secret.name}-secret`"
                                    :state="
                                        !secret.value
                                            ? isVariableOptional(secret.name, 'secret')
                                                ? null
                                                : false
                                            : true
                                    "
                                    :placeholder="getVariableTitle(secret.name, 'secret')"
                                    :title="getVariableTitle(secret.name, 'secret')"
                                    :aria-label="getVariableTitle(secret.name, 'secret')"
                                    :required="!isVariableOptional(secret.name, 'secret')"
                                    :readonly="false"
                                    class="mb-2" />
                            </div>
                        </div>
                    </template>
                </GCard>

                <div class="d-flex flex-gapx-1 justify-content-center">
                    <GButton color="blue" outline title="Create a new set of credentials" @click="onCreateNewSet">
                        <FontAwesomeIcon :icon="faPlus" />
                        Create New Set
                    </GButton>

                    <GButton color="grey" outline title="Clear selection" @click="onClearSelection">
                        <FontAwesomeIcon :icon="faXmark" />
                        Clear Selection
                    </GButton>
                </div>
            </div>
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
