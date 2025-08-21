<script setup lang="ts">
import {
    faBan,
    faCaretRight,
    faCheck,
    faPencilAlt,
    faPlus,
    faSave,
    faSpinner,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BCollapse, BFormGroup, BFormInput } from "bootstrap-vue";
import { faX, faXmark } from "font-awesome-6";
import { computed, ref } from "vue";

import type {
    CreateSourceCredentialsPayload,
    ServiceCredentialPayload,
    ServiceGroupPayload,
    ServiceVariableDefinition,
} from "@/api/users";
import type { CardAction, CardIndicator } from "@/components/Common/GCard.types";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useToolCredentialsDefinitionsStore } from "@/stores/toolCredentialsDefinitionsStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";

type CredentialType = "variable" | "secret";

interface Props {
    toolId: string;
    toolVersion: string;
    credentialPayload: ServiceCredentialPayload;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "new-credentials-set", newSet: ServiceGroupPayload): void;
    (e: "update-current-set", newSet?: ServiceGroupPayload): void;
}>();

const { confirm } = useConfirmDialog();
const { getServiceCredentialsDefinition } = useToolCredentialsDefinitionsStore();
const { isBusy, busyMessage, saveUserCredentials, deleteCredentialsGroup } = useUserToolCredentials(
    props.toolId,
    props.toolVersion
);

const isExpanded = ref(false);
const saveButtonText = ref("Save");
const editSet = ref<Record<string, { data: ServiceGroupPayload }>>({});

const availableSets = computed<ServiceGroupPayload[]>(() => props.credentialPayload.groups);
const serviceCredentialsDefinition = computed(() => {
    const scd = getServiceCredentialsDefinition(props.toolId, props.toolVersion, props.credentialPayload);

    if (!scd) {
        throw new Error(
            `Service credentials definition not found for tool ${props.toolId} version ${props.toolVersion}`
        );
    }

    return scd;
});

const selectedSet = computed<ServiceGroupPayload | undefined>(() =>
    props.credentialPayload.groups.find((group) => group.name === props.credentialPayload.current_group)
);
const serviceName = computed<string>(
    () => serviceCredentialsDefinition.value.label || serviceCredentialsDefinition.value.name
);
const disableSaveButton = computed(() => {
    return (editingSetKey: string) => {
        if (!editSet.value[editingSetKey]) {
            return true;
        }

        const newData = editSet.value[editingSetKey].data;

        return (
            isBusy.value ||
            !newData.name ||
            newData.variables.some((variable) => !variable.value && !isVariableOptional(variable.name, "variable")) ||
            newData.secrets.some((secret) => !secret.value && !isVariableOptional(secret.name, "secret")) ||
            availableSets.value.filter((set) => set.name === newData.name).length > 1
        );
    };
});

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
    const definition = serviceCredentialsDefinition.value[type === "variable" ? "variables" : "secrets"].find(
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
    const newSet: ServiceGroupPayload = {
        name: generateUniqueName("new credential", props.credentialPayload.groups),
        variables: serviceCredentialsDefinition.value.variables.map((variable) => ({
            name: variable.name,
            value: null,
        })),
        secrets: serviceCredentialsDefinition.value.secrets.map((secret) => ({
            name: secret.name,
            value: null,
        })),
    };

    emit("new-credentials-set", newSet);

    onEditSet(newSet.name);
}

function onCurrentSetChange(selectedSet?: ServiceGroupPayload) {
    emit("update-current-set", selectedSet);
}

async function onDeleteSet(setToDelete: ServiceGroupPayload) {
    const confirmed = await confirm(`Are you sure you want to delete the credentials set "${setToDelete.name}"?`, {
        title: "Delete credentials set",
        okTitle: "Delete set",
        okVariant: "danger",
        cancelVariant: "outline-primary",
        centered: true,
    });

    if (confirmed && setToDelete) {
        await deleteCredentialsGroup(props.credentialPayload, setToDelete.name);
    }
}

function onDiscardSet(setName: string) {
    delete editSet.value[setName];

    editSet.value = { ...editSet.value };
}

function onEditSet(setName: string) {
    editSet.value = {
        ...editSet.value,
        [setName]: { data: { ...availableSets.value.find((set) => set.name === setName)! } },
    };
}

async function onSaveSet(setName: string) {
    try {
        if (!editSet.value[setName]) {
            return;
        }

        saveButtonText.value = busyMessage.value;

        const toSend: CreateSourceCredentialsPayload = {
            source_id: props.toolId,
            source_type: "tool",
            source_version: props.toolVersion,
            credentials: [{ ...props.credentialPayload, groups: [editSet.value[setName].data] }],
        };

        await saveUserCredentials(toSend);

        onDiscardSet(setName);
    } catch (e) {
        Toast.error(`Error saving credentials: ${errorMessageAsString(e)}`);
    } finally {
        saveButtonText.value = "Save";
    }
}

function primaryActions(setData: ServiceGroupPayload): CardAction[] {
    return [
        {
            id: `delete-${setData.name}`,
            label: "",
            title: "Delete this set",
            icon: faTrash,
            variant: "outline-danger",
            handler: () => onDeleteSet(setData),
            visible: setData.name !== selectedSet.value?.name && !editSet.value[setData.name],
        },
        {
            id: `edit-${setData.name}`,
            label: "Edit",
            title: "Edit this set",
            icon: faPencilAlt,
            variant: "outline-info",
            handler: () => onEditSet(setData.name),
            visible: !editSet.value[setData.name],
        },
        {
            id: `use-${setData.name}`,
            label: selectedSet.value?.name === setData.name ? "This set is currently used" : "Use this set",
            title: "Use this set",
            icon: selectedSet.value?.name === setData.name ? faX : faCheck,
            variant: "outline-info",
            handler: () => onCurrentSetChange(setData),
            disabled: selectedSet.value?.name === setData.name,
            visible: !editSet.value[setData.name] && selectedSet.value?.name !== setData.name,
        },
        {
            id: `discard-${setData.name}`,
            label: "Discard",
            title: "Discard changes to this set",
            icon: faBan,
            variant: "outline-danger",
            handler: () => onDiscardSet(setData.name),
            disabled: isBusy.value,
            visible: !!editSet.value[setData.name],
        },
        {
            id: `save-${setData.name}`,
            label: "Save",
            title: "Save changes to this set",
            icon: isBusy.value ? faSpinner : faSave,
            variant: "outline-info",
            handler: () => onSaveSet(setData.name),
            disabled: disableSaveButton.value(setData.name),
            visible: !!editSet.value[setData.name],
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
        }
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
                    <span v-if="selectedSet">
                        Using: <b>{{ selectedSet?.name }}</b>
                    </span>
                    <span v-else> No credential set</span>
                </span>
            </BButton>
        </div>

        <BCollapse :id="`accordion-${serviceCredentialsDefinition.name}`" v-model="isExpanded" class="px-2">
            <div class="d-flex flex-column align-items-center mt-2">
                <span class="text-md">{{ serviceCredentialsDefinition.description }}</span>

                <GCard
                    v-for="avs in availableSets"
                    :id="`set-${avs.name}`"
                    :key="avs.name"
                    :title="avs.name"
                    :selected="selectedSet?.name === avs.name && !editSet[avs.name]"
                    :indicators="setIndicators(avs.name)"
                    :primary-actions="primaryActions(avs)">
                    <template v-if="editSet[avs.name]" v-slot:description>
                        <div class="p-2">
                            Editing set of credentials for <b>{{ avs.name }}</b>

                            <BFormGroup
                                :id="`${avs.name}-name`"
                                label="Set Name"
                                description="Enter a unique name for the set of credentials">
                                <BFormInput
                                    :id="`${avs.name}-name-input`"
                                    :value="editSet[avs.name]?.data.name"
                                    type="text"
                                    :state="editSet[avs.name]?.data.name ? true : false"
                                    placeholder="Enter set name"
                                    title="Set Name"
                                    aria-label="Set Name"
                                    class="mb-2"
                                    @input="(newValue) => onNameInput(avs.name, newValue)" />
                            </BFormGroup>

                            <div v-for="variable in editSet[avs.name]?.data.variables" :key="variable.name">
                                <BFormGroup
                                    :id="`${editSet[avs.name]?.data.name}-${variable.name}-variable`"
                                    :label="getVariableTitle(variable.name, 'variable')"
                                    :description="getVariableDescription(variable.name, 'variable')">
                                    <BFormInput
                                        :id="`${editSet[avs.name]?.data.name}-${variable.name}-variable-input`"
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
                                </BFormGroup>
                            </div>

                            <div v-for="secret in editSet[avs.name]?.data.secrets" :key="secret.name">
                                <BFormGroup
                                    :id="`${editSet[avs.name]?.data.name}-${secret.name}-secret`"
                                    :label="getVariableTitle(secret.name, 'secret')"
                                    :description="getVariableDescription(secret.name, 'secret')">
                                    <BFormInput
                                        :id="`${editSet[avs.name]?.data.name}-${secret.name}-secret-input`"
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
                                </BFormGroup>
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
