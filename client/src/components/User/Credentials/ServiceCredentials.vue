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
    ServiceCredentialsDefinition,
    ServiceCredentialsGroup,
    ServiceGroupPayload,
} from "@/api/users";
import type { CardAction, CardIndicator } from "@/components/Common/GCard.types";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { SECRET_PLACEHOLDER, useUserToolsServicesStore } from "@/stores/userToolsServicesStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";

type CredentialType = "variable" | "secret";
interface EditGroup {
    groupId: string;
    groupPayload: ServiceGroupPayload;
    newGroup: boolean;
}

interface Props {
    sourceId: string;
    sourceVersion: string;
    serviceDefinition: ServiceCredentialsDefinition;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update-current-group", groupId?: string): void;
}>();

const { confirm } = useConfirmDialog();

const isExpanded = ref(false);
const saveButtonText = ref("Save");

const editingGroups = ref<Record<string, EditGroup>>({});

const sourceId = computed(() => props.sourceId);
const sourceVersion = computed(() => props.sourceVersion);

const userToolsServicesStore = useUserToolsServicesStore();

const {
    isBusy,
    busyMessage,
    userServiceGroupsFor,
    createUserCredentials,
    saveUserCredentials,
    deleteCredentialsGroup,
} = useUserToolCredentials(sourceId.value, sourceVersion.value);

const toolService = computed(() => {
    return userToolsServicesStore.getToolService(sourceId.value, sourceVersion.value, props.serviceDefinition);
});
const serviceGroups = computed<ServiceCredentialsGroup[]>(() => {
    return userServiceGroupsFor.value(props.serviceDefinition) ?? [];
});
const selectedGroup = computed<ServiceCredentialsGroup | undefined>(() =>
    serviceGroups.value.find((group) => group.id === toolService.value?.current_group_id)
);
const serviceName = computed<string>(() => props.serviceDefinition.label || props.serviceDefinition.name);
const disableSaveButton = computed(() => {
    return (editingGroupKey: string) => {
        if (!editingGroups.value[editingGroupKey]) {
            return true;
        }

        const newData = editingGroups.value[editingGroupKey].groupPayload;

        return (
            isBusy.value ||
            !newData.name ||
            newData.variables.some((variable) => !variable.value && !isVariableOptional(variable.name, "variable")) ||
            newData.secrets.some((secret) => !secret.value && !isVariableOptional(secret.name, "secret")) ||
            serviceGroups.value.filter((group) => group.name === newData.name).length > 1
        );
    };
});

function generateUniqueName(template: string, currentGroups: ServiceCredentialsGroup[]): string {
    let name = template;
    let counter = 1;
    while (currentGroups.some((group) => group.name === name)) {
        name = `${template} ${counter}`;
        counter++;
    }
    return name;
}

function getVariableDefinition(name: string, type: CredentialType) {
    const definition = props.serviceDefinition[type === "variable" ? "variables" : "secrets"].find(
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

function onCreateTemporaryGroup() {
    const editableGroup: ServiceGroupPayload = {
        name: generateUniqueName("new credential", serviceGroups.value),
        variables: props.serviceDefinition.variables.map((variable) => ({
            name: variable.name,
            value: "",
        })),
        secrets: props.serviceDefinition.secrets.map((secret) => ({
            name: secret.name,
            value: "",
        })),
    };

    editingGroups.value = {
        ...editingGroups.value,
        [editableGroup.name]: { groupId: editableGroup.name, groupPayload: editableGroup, newGroup: true },
    };
}

function onEditGroup(groupId: string) {
    const groupToEdit = serviceGroups.value.find((group) => group.id === groupId);

    if (!groupToEdit) {
        throw new Error(`Group not found: ${groupId}`);
    }

    const editableGroup: ServiceGroupPayload = {
        name: groupToEdit.name,
        secrets: groupToEdit.secrets.map((secret) => ({
            name: secret.name,
            value: secret.is_set ? SECRET_PLACEHOLDER : "",
        })),
        variables: groupToEdit.variables.map((variable) => ({
            name: variable.name,
            value: variable.value,
        })),
    };

    editingGroups.value = {
        ...editingGroups.value,
        [groupId]: { groupId: groupToEdit.id, groupPayload: editableGroup, newGroup: false },
    };
}

function onDiscardGroup(groupId: string) {
    delete editingGroups.value[groupId];

    editingGroups.value = { ...editingGroups.value };
}

function onCurrentGroupChange(selectedGroup?: ServiceCredentialsGroup) {
    emit("update-current-group", selectedGroup?.id);
}

async function onCreateGroup(editGroup: EditGroup) {
    try {
        const newGroup: CreateSourceCredentialsPayload = {
            source_id: sourceId.value,
            source_type: "tool",
            source_version: sourceVersion.value,
            service_credential: {
                name: props.serviceDefinition.name,
                version: props.serviceDefinition.version,
                group: editGroup.groupPayload,
            },
        };

        await createUserCredentials(newGroup);

        onDiscardGroup(editGroup?.groupId);
    } catch (e) {
        Toast.error(`Error creating group: ${errorMessageAsString(e)}`);
    }
}

async function onUpdateGroup(groupId: string) {
    try {
        const groupToUpdate = editingGroups.value[groupId];

        if (!groupToUpdate) {
            return;
        }

        saveButtonText.value = busyMessage.value;

        await saveUserCredentials(groupId, groupToUpdate.groupPayload);

        onDiscardGroup(groupId);
    } catch (e) {
        Toast.error(`Error saving credentials: ${errorMessageAsString(e)}`);
    } finally {
        saveButtonText.value = "Save";
    }
}

async function onDeleteGroup(groupToDelete: ServiceCredentialsGroup) {
    const confirmed = await confirm(`Are you sure you want to delete the credentials group "${groupToDelete.name}"?`, {
        title: "Delete credentials group",
        okTitle: "Delete group",
        okVariant: "danger",
        cancelVariant: "outline-primary",
        centered: true,
    });

    if (confirmed && groupToDelete) {
        await deleteCredentialsGroup(props.serviceDefinition, groupToDelete.id);
    }
}

function primaryActions(groupData: ServiceCredentialsGroup): CardAction[] {
    return [
        {
            id: `delete-${groupData.name}`,
            label: "",
            title: "Delete this group",
            icon: faTrash,
            variant: "outline-danger",
            handler: () => onDeleteGroup(groupData),
            visible: groupData.name !== selectedGroup.value?.name && !editingGroups.value[groupData.id],
        },
        {
            id: `edit-${groupData.name}`,
            label: "Edit",
            title: "Edit this group",
            icon: faPencilAlt,
            variant: "outline-info",
            handler: () => onEditGroup(groupData.id),
            visible: !editingGroups.value[groupData.id],
        },
        {
            id: `use-${groupData.name}`,
            label: selectedGroup.value?.name === groupData.name ? "This group is currently used" : "Use this group",
            title: "Use this group",
            icon: selectedGroup.value?.name === groupData.name ? faX : faCheck,
            variant: "outline-info",
            handler: () => onCurrentGroupChange(groupData),
            disabled: selectedGroup.value?.name === groupData.name,
            visible: !editingGroups.value[groupData.id] && selectedGroup.value?.name !== groupData.name,
        },
        {
            id: `discard-${groupData.name}`,
            label: "Discard",
            title: "Discard changes to this group",
            icon: faBan,
            variant: "outline-danger",
            handler: () => onDiscardGroup(groupData.id),
            disabled: isBusy.value,
            visible: !!editingGroups.value[groupData.id],
        },
        {
            id: `save-${groupData.name}`,
            label: "Save",
            title: "Save changes to this group",
            icon: isBusy.value ? faSpinner : faSave,
            variant: "outline-info",
            handler: () => onUpdateGroup(groupData.id),
            disabled: disableSaveButton.value(groupData.id),
            visible: !!editingGroups.value[groupData.id],
        },
    ];
}

function primaryActionsForNewGroup(eg: EditGroup): CardAction[] {
    const groupName = eg.groupPayload.name;
    return [
        {
            id: `discard-${groupName}`,
            label: "Discard",
            title: "Discard changes to this group",
            icon: faBan,
            variant: "outline-danger",
            handler: () => onDiscardGroup(groupName),
            disabled: isBusy.value,
            visible: !!editingGroups.value[groupName],
        },
        {
            id: `save-${groupName}`,
            label: "Save",
            title: "Save changes to this group",
            icon: isBusy.value ? faSpinner : faSave,
            variant: "outline-info",
            handler: () => onCreateGroup(eg),
            disabled: disableSaveButton.value(groupName),
            visible: !!editingGroups.value[groupName],
        },
    ];
}

function groupIndicators(groupName: string): CardIndicator[] {
    return [
        {
            id: "current-group",
            label: "",
            title: "This group will be used for this tool in the workflow",
            icon: faCheck,
            visible: selectedGroup.value?.name === groupName,
        },
    ];
}

function onClearSelection() {
    onCurrentGroupChange(undefined);
}

function onNameInput(groupId: string, value?: string) {
    if (editingGroups.value[groupId]) {
        editingGroups.value[groupId].groupPayload.name = value?.trim() || "";
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

                <span class="text-muted selected-group-info">
                    <span v-if="selectedGroup">
                        Using: <b>{{ selectedGroup?.name }}</b>
                    </span>
                    <span v-else> No credential group selected</span>
                </span>
            </BButton>
        </div>

        <BCollapse :id="`accordion-${props.serviceDefinition.name}`" v-model="isExpanded" class="px-2">
            <div class="d-flex flex-column align-items-center mt-2">
                <span class="text-md">{{ props.serviceDefinition.description }}</span>

                <GCard
                    v-for="sg in serviceGroups"
                    :id="`group-${sg.id}-${sg.name}`"
                    :key="`${sg.id}-${sg.name}`"
                    :title="sg.name"
                    :selected="selectedGroup?.name === sg.name && !editingGroups[sg.id]"
                    :indicators="groupIndicators(sg.name)"
                    :primary-actions="primaryActions(sg)">
                    <template v-if="editingGroups[sg.id]" v-slot:description>
                        <div class="p-2">
                            Editing group of credentials for <b>{{ sg.name }}</b>

                            <BFormGroup
                                :id="`${sg.name}-name`"
                                label="Group Name"
                                description="Enter a unique name for this group">
                                <BFormInput
                                    :id="`${sg.name}-name-input`"
                                    :value="editingGroups[sg.id]?.groupPayload.name"
                                    type="text"
                                    :state="editingGroups[sg.id]?.groupPayload.name ? true : false"
                                    placeholder="Enter group name"
                                    title="Group Name"
                                    aria-label="Group Name"
                                    class="mb-2"
                                    @input="(newValue) => onNameInput(sg.id, newValue)" />
                            </BFormGroup>

                            <div v-for="variable in editingGroups[sg.id]?.groupPayload.variables" :key="variable.name">
                                <BFormGroup
                                    :id="`${editingGroups[sg.id]?.groupPayload.name}-${variable.name}-variable`"
                                    :label="getVariableTitle(variable.name, 'variable')"
                                    :description="getVariableDescription(variable.name, 'variable')">
                                    <BFormInput
                                        :id="`${editingGroups[sg.id]?.groupPayload.name}-${
                                            variable.name
                                        }-variable-input`"
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

                            <div v-for="secret in editingGroups[sg.id]?.groupPayload.secrets" :key="secret.name">
                                <BFormGroup
                                    :id="`${editingGroups[sg.id]?.groupPayload.name}-${secret.name}-secret`"
                                    :label="getVariableTitle(secret.name, 'secret')"
                                    :description="getVariableDescription(secret.name, 'secret')">
                                    <BFormInput
                                        :id="`${editingGroups[sg.id]?.groupPayload.name}-${secret.name}-secret-input`"
                                        v-model="secret.value"
                                        type="password"
                                        autocomplete="off"
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

                <GCard
                    v-for="eg in Object.values(editingGroups).filter((g) => !g.groupId)"
                    :key="eg.groupId"
                    :title="eg.groupId"
                    :primary-actions="primaryActionsForNewGroup(eg)"
                    class="mb-2">
                    <template v-slot:description>
                        <div class="p-2">
                            Creating new group of credentials

                            <BFormGroup
                                :id="`${eg.groupId}-name`"
                                label="Group Name"
                                description="Enter a unique name for this group">
                                <BFormInput
                                    :id="`${eg.groupId}-name-input`"
                                    :value="eg.groupPayload.name"
                                    type="text"
                                    :state="eg.groupPayload.name ? true : false"
                                    placeholder="Enter group name"
                                    title="Group Name"
                                    aria-label="Group Name"
                                    class="mb-2"
                                    @input="(newValue) => onNameInput(eg.groupId, newValue)" />
                            </BFormGroup>

                            <div
                                v-for="variable in eg.groupPayload.variables"
                                :key="`${eg.groupId}-${variable.name}-variable`">
                                <BFormGroup
                                    :id="`${eg.groupId}-${variable.name}-variable`"
                                    :label="getVariableTitle(variable.name, 'variable')"
                                    :description="getVariableDescription(variable.name, 'variable')">
                                    <BFormInput
                                        :id="`${eg.groupId}-${variable.name}-variable-input`"
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

                            <div v-for="secret in eg.groupPayload.secrets" :key="`${eg.groupId}-${secret.name}-secret`">
                                <BFormGroup
                                    :id="`${eg.groupId}-${secret.name}-secret`"
                                    :label="getVariableTitle(secret.name, 'secret')"
                                    :description="getVariableDescription(secret.name, 'secret')">
                                    <BFormInput
                                        :id="`${eg.groupId}-${secret.name}-secret-input`"
                                        v-model="secret.value"
                                        type="password"
                                        autocomplete="off"
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
                    <GButton
                        color="blue"
                        outline
                        title="Create a new group of credentials"
                        @click="onCreateTemporaryGroup">
                        <FontAwesomeIcon :icon="faPlus" />
                        Create New Group
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

.selected-group-info {
    font-size: 0.8rem;
    font-weight: normal;
    align-self: center;
}
</style>
