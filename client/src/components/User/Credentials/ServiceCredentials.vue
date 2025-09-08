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
import { BBadge, BButton, BCollapse } from "bootstrap-vue";
import { faX, faXmark } from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { CredentialType } from "@/api/userCredentials";
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
import { SECRET_PLACEHOLDER, useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";
import CredentialsGroupForm from "@/components/User/Credentials/CredentialsGroupForm.vue";

interface EditGroup {
    groupId: string;
    isNewGroup: boolean;
    groupPayload: ServiceGroupPayload;
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

const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
const { isBusy, busyMessage, getUserToolServiceCurrentGroupId } = storeToRefs(userToolsServiceCredentialsStore);

const { userServiceGroupsFor, userServiceFor, createUserCredentials, saveUserCredentials, deleteCredentialsGroup } =
    useUserToolCredentials(sourceId.value, sourceVersion.value);

const serviceName = computed<string>(() => {
    return props.serviceDefinition.label || props.serviceDefinition.name || "Unknown Service";
});

const userServicesGroups = computed<ServiceCredentialsGroup[]>(() => {
    return userServiceGroupsFor.value(props.serviceDefinition) ?? [];
});

const userToolService = userServiceFor.value(props.serviceDefinition);

const currentServiceCredentialsGroup = computed(() => {
    if (!userToolService?.id) {
        return undefined;
    }
    const currentGroupId = getUserToolServiceCurrentGroupId.value(
        props.sourceId,
        props.sourceVersion,
        userToolService.id
    );
    return userServicesGroups.value.find((group) => group.id === currentGroupId);
});

const newEditingGroups = computed(() => {
    return Object.values(editingGroups.value).filter((g) => g.isNewGroup);
});

function isVariableOptional(name: string, type: CredentialType): boolean {
    const definitions = type === "variable" ? props.serviceDefinition.variables : props.serviceDefinition.secrets;
    const definition = definitions.find((variable) => variable.name === name);
    return definition?.optional || false;
}

function validateGroupData(groupData: ServiceGroupPayload): boolean {
    if (!groupData.name?.trim()) {
        return false;
    }

    const hasInvalidVariable = groupData.variables.some(
        (variable) => !variable.value && !isVariableOptional(variable.name, "variable")
    );

    const hasInvalidSecret = groupData.secrets.some(
        (secret) => !secret.value && !isVariableOptional(secret.name, "secret")
    );

    const hasDuplicateName = userServicesGroups.value.filter((group) => group.name === groupData.name).length > 1;

    return !hasInvalidVariable && !hasInvalidSecret && !hasDuplicateName;
}

const disableSaveButton = computed(() => {
    return (editingGroupKey: string): boolean => {
        const editGroup = editingGroups.value[editingGroupKey];
        if (!editGroup) {
            return true;
        }

        return isBusy.value || !validateGroupData(editGroup.groupPayload);
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

function createTemporaryGroup() {
    const editableGroup: ServiceGroupPayload = {
        name: generateUniqueName("new credential", userServicesGroups.value),
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
        [editableGroup.name]: {
            groupId: editableGroup.name,
            groupPayload: editableGroup,
            isNewGroup: true,
        },
    };
}

function editGroup(groupId: string) {
    const groupToEdit = userServicesGroups.value.find((group) => group.id === groupId);

    if (!groupToEdit) {
        Toast.error(`Group not found: ${groupId}`);
        return;
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
        [groupId]: {
            groupId: groupToEdit.id,
            isNewGroup: false,
            groupPayload: editableGroup,
        },
    };
}

function discardGroupChanges(groupId: string) {
    const { [groupId]: _removedGroup, ...remainingGroups } = editingGroups.value;
    editingGroups.value = remainingGroups;
}

function updateCurrentGroup(selectedGroup?: ServiceCredentialsGroup) {
    emit("update-current-group", selectedGroup?.id);
}

function onClearSelection() {
    updateCurrentGroup(undefined);
}

async function createGroup(editGroup: EditGroup) {
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

        discardGroupChanges(editGroup.groupId);

        Toast.success("Credentials group created successfully");
    } catch (error) {
        console.error("Error creating group:", error);
        Toast.error(`${errorMessageAsString(error)}`);
    }
}

async function updateGroup(groupId: string) {
    try {
        const groupToUpdate = editingGroups.value[groupId];

        if (!groupToUpdate) {
            console.warn(`No group found for update: ${groupId}`);
            return;
        }

        saveButtonText.value = busyMessage.value;

        await saveUserCredentials(groupId, groupToUpdate.groupPayload);

        discardGroupChanges(groupId);

        Toast.success("Credentials group updated successfully");
    } catch (error) {
        console.error("Error saving credentials:", error);
        Toast.error(`${errorMessageAsString(error)}`);
    } finally {
        saveButtonText.value = "Save";
    }
}

async function deleteGroup(groupToDelete: ServiceCredentialsGroup) {
    const confirmed = await confirm(`Are you sure you want to delete the credentials group "${groupToDelete.name}"?`, {
        title: "Delete credentials group",
        okTitle: "Delete group",
        okVariant: "danger",
        cancelVariant: "outline-primary",
        centered: true,
    });

    if (confirmed && groupToDelete) {
        try {
            await deleteCredentialsGroup(props.serviceDefinition, groupToDelete.id);
            Toast.success("Credentials group deleted successfully");
        } catch (error) {
            console.error("Error deleting group:", error);
            Toast.error(`Error deleting group: ${errorMessageAsString(error)}`);
        }
    }
}

const primaryActions = computed(() => (groupData: ServiceCredentialsGroup): CardAction[] => {
    const editingGroup = editingGroups.value[groupData.id];
    const isBeingEdited = Boolean(editingGroup);
    const isCurrentGroup = currentServiceCredentialsGroup.value?.id === groupData.id;

    return [
        {
            id: `delete-${groupData.id}`,
            label: "",
            title: isCurrentGroup
                ? "Cannot delete the group currently in use. Clear selection first."
                : "Delete this group (cannot be undone)",
            icon: faTrash,
            variant: "outline-danger",
            handler: () => deleteGroup(groupData),
            disabled: isBusy.value || isCurrentGroup,
            visible: !isBeingEdited,
        },
        {
            id: `edit-${groupData.name}`,
            label: "Edit",
            title: "Edit this group",
            icon: faPencilAlt,
            variant: "outline-info",
            handler: () => editGroup(groupData.id),
            visible: !isBeingEdited,
        },
        {
            id: `use-${groupData.name}`,
            label: isCurrentGroup ? "This group is currently used" : "Use this group",
            title: "Use this group",
            icon: isCurrentGroup ? faX : faCheck,
            variant: "outline-info",
            handler: () => updateCurrentGroup(groupData),
            disabled: isBusy.value,
            visible: !isBeingEdited && !isCurrentGroup,
        },
        {
            id: `discard-${groupData.name}`,
            label: "Discard",
            title: "Discard changes to this group",
            icon: faBan,
            variant: "outline-danger",
            handler: () => discardGroupChanges(groupData.id),
            disabled: isBusy.value,
            visible: isBeingEdited,
        },
        {
            id: `save-${groupData.name}`,
            label: "Save Changes",
            title: "Save changes to this group",
            icon: isBusy.value ? faSpinner : faSave,
            variant: "outline-info",
            handler: () => updateGroup(groupData.id),
            disabled: disableSaveButton.value(groupData.id),
            visible: isBeingEdited,
        },
    ];
});

const primaryActionsForNewGroup = computed(() => (editGroup: EditGroup): CardAction[] => {
    const groupId = editGroup.groupId;
    const isBeingEdited = Boolean(editingGroups.value[groupId]);

    return [
        {
            id: `discard-${groupId}`,
            label: "Discard",
            title: "Discard changes to this group",
            icon: faBan,
            variant: "outline-danger",
            handler: () => discardGroupChanges(groupId),
            disabled: isBusy.value,
            visible: isBeingEdited,
        },
        {
            id: `save-${groupId}`,
            label: "Create Group",
            title: "Save changes to this group",
            icon: isBusy.value ? faSpinner : faSave,
            variant: "outline-info",
            handler: () => createGroup(editGroup),
            disabled: disableSaveButton.value(groupId),
            visible: isBeingEdited,
        },
    ];
});

const groupIndicators = computed(() => (group: ServiceCredentialsGroup): CardIndicator[] => {
    const isCurrentGroup = currentServiceCredentialsGroup.value?.id === group.id;
    const isBeingEdited = Boolean(editingGroups.value[group.id]);

    return [
        {
            id: "current-group",
            label: "",
            title: "This group will be used for this tool in the workflow",
            icon: faCheck,
            visible: isCurrentGroup && !isBeingEdited,
        },
    ];
});
</script>

<template>
    <div>
        <div>
            <BButton class="service-title" block variant="outline-info" @click="isExpanded = !isExpanded">
                <span class="d-flex align-items-center flex-gapx-1">
                    <FontAwesomeIcon v-if="!isExpanded" :icon="faCaretRight" />
                    <FontAwesomeIcon v-else :icon="faCaretRight" rotation="90" />
                    {{ serviceName }}

                    <template v-if="!currentServiceCredentialsGroup?.id">
                        <BBadge
                            v-if="props.serviceDefinition.optional"
                            v-b-tooltip.hover.noninteractive
                            pill
                            title="This service is optional. You may choose not to provide credentials for it."
                            variant="secondary"
                            class="outline-badge">
                            Optional
                        </BBadge>
                        <BBadge
                            v-else
                            v-b-tooltip.hover.noninteractive
                            pill
                            title="This service is required. The tool may not function properly without providing credentials for it."
                            :variant="currentServiceCredentialsGroup ? 'success' : 'warning'"
                            class="outline-badge">
                            Required
                        </BBadge>
                    </template>
                </span>

                <span class="font-weight-normal align-self-center text-muted selected-group-info">
                    <span v-if="currentServiceCredentialsGroup?.id" class="d-flex align-items-center flex-gapx-1">
                        <FontAwesomeIcon :icon="faCheck" class="text-success" />
                        Using: <b>{{ currentServiceCredentialsGroup?.name }}</b>
                    </span>
                    <span v-else> No credential group selected </span>
                </span>
            </BButton>
        </div>

        <BCollapse :id="`accordion-${props.serviceDefinition.name}`" v-model="isExpanded" class="px-2">
            <div class="d-flex flex-column mt-2">
                <span class="text-md">{{ props.serviceDefinition.description }}</span>

                <div class="d-flex flex-gapx-1 justify-content-center my-2">
                    <GButton
                        color="blue"
                        outline
                        title="Create a new group of credentials"
                        :disabled="editingGroups && Object.keys(editingGroups).length > 0"
                        @click="createTemporaryGroup">
                        <FontAwesomeIcon :icon="faPlus" />
                        Create New Group
                    </GButton>

                    <GButton
                        color="grey"
                        outline
                        title="Clear selection"
                        :disabled="!currentServiceCredentialsGroup?.id"
                        @click="onClearSelection">
                        <FontAwesomeIcon :icon="faXmark" />
                        Clear Selection
                    </GButton>
                </div>

                <GCard
                    v-for="neg in newEditingGroups"
                    :id="`group-${neg.groupId}`"
                    :key="neg.groupId"
                    :title="neg.groupId"
                    :primary-actions="primaryActionsForNewGroup(neg)"
                    class="mb-2">
                    <template v-slot:description>
                        <CredentialsGroupForm :group-data="neg" :service-definition="props.serviceDefinition" />
                    </template>
                </GCard>

                <GCard
                    v-for="usg in userServicesGroups"
                    :id="`group-${usg.id}-${usg.name}`"
                    :key="`${usg.id}-${usg.name}`"
                    :title="usg.name"
                    :selected="currentServiceCredentialsGroup?.id === usg.id && !editingGroups[usg.id]"
                    :indicators="groupIndicators(usg)"
                    :primary-actions="primaryActions(usg)">
                    <template v-if="editingGroups[usg.id]" v-slot:description>
                        <CredentialsGroupForm
                            :group-data="editingGroups[usg.id]"
                            :service-definition="props.serviceDefinition" />
                    </template>
                </GCard>
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

    .selected-group-info {
        font-size: 0.8rem;
    }
}
</style>
