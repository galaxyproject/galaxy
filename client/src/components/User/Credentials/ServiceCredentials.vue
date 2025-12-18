<script setup lang="ts">
/**
 * ServiceCredentials Component
 *
 * A collapsible component for managing service credentials for a specific tool.
 * Provides functionality to create, edit, delete, and select credential groups
 * with validation and real-time updates.
 *
 * Features:
 * - Expandable/collapsible interface
 * - Create new credential groups
 * - Edit existing credential groups inline
 * - Delete credential groups with confirmation
 * - Select current group for tool execution
 * - Validation for required/optional fields
 * - Visual indicators for current group selection
 * - Temporary editing state management
 *
 * @component ServiceCredentials
 * @example
 * <ServiceCredentials
 *   :source-id="toolId"
 *   :source-version="toolVersion"
 *   :service-definition="serviceDefinition"
 *   @update-current-group="onGroupChange" />
 */

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

import type {
    CreateSourceCredentialsPayload,
    CredentialType,
    ServiceCredentialGroupPayload,
    ServiceCredentialGroupResponse,
    ServiceCredentialsDefinition,
} from "@/api/userCredentials";
import type { CardAction, CardIndicator } from "@/components/Common/GCard.types";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { SECRET_PLACEHOLDER, useUserToolsServiceCredentialsStore } from "@/stores/userToolsServiceCredentialsStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";
import CredentialsGroupForm from "@/components/User/Credentials/CredentialsGroupForm.vue";

/**
 * Edit group structure for temporary editing state
 * @interface EditGroup
 */
interface EditGroup {
    /** Group ID being edited */
    groupId: string;
    /** Whether this is a new group being created */
    isNewGroup: boolean;
    /** Group payload data */
    groupPayload: ServiceCredentialGroupPayload;
}

interface Props {
    /**
     * Source tool ID
     * @type {string}
     */
    sourceId: string;

    /**
     * Source tool version
     * @type {string}
     */
    sourceVersion: string;

    /**
     * Service definition configuration
     * @type {ServiceCredentialsDefinition}
     */
    serviceDefinition: ServiceCredentialsDefinition;
}

const props = defineProps<Props>();

/**
 * Events emitted to parent components
 */
const emit = defineEmits<{
    /**
     * Emitted when the current group selection changes
     * @event update-current-group
     * @param {string} [groupId] - ID of the selected group, undefined to clear selection
     */
    (e: "update-current-group", groupId?: string): void;
}>();

const { confirm } = useConfirmDialog();

/** Controls expansion state of the service section */
const isExpanded = ref(false);
/** Text for the save button */
const saveButtonText = ref("Save");
/** Map of groups currently being edited */
const editingGroups = ref<Record<string, EditGroup>>({});

/** Computed source ID from props */
const sourceId = computed(() => props.sourceId);
/** Computed source version from props */
const sourceVersion = computed(() => props.sourceVersion);

const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
const { isBusy, busyMessage, getUserToolServiceCurrentGroupId } = storeToRefs(userToolsServiceCredentialsStore);

const { userServiceGroupsFor, userServiceFor, createUserCredentials, saveUserCredentials, deleteCredentialsGroup } =
    useUserToolCredentials(sourceId.value, sourceVersion.value);

/**
 * Display name for the service
 * @returns {string} Service label, name, or fallback
 */
const serviceName = computed<string>(() => {
    return props.serviceDefinition.label || props.serviceDefinition.name || "Unknown Service";
});

/**
 * Available credential groups for this service
 * @returns {ServiceCredentialGroupResponse[]} Array of credential groups
 */
const userServicesGroups = computed<ServiceCredentialGroupResponse[]>(() => {
    return userServiceGroupsFor.value(props.serviceDefinition) ?? [];
});

/**
 * Currently selected credential group for this service
 * @returns {ServiceCredentialGroupResponse | undefined} Current group or undefined
 */
const currentServiceCredentialsGroup = computed(() => {
    const userToolService = userServiceFor.value(props.serviceDefinition);

    if (!userToolService?.id) {
        return undefined;
    }
    const currentGroupId = getUserToolServiceCurrentGroupId.value(
        props.sourceId,
        props.sourceVersion,
        userToolService.id,
    );
    return userServicesGroups.value.find((group) => group.id === currentGroupId);
});

/**
 * Filter to get only new groups being created
 * @returns {EditGroup[]} Array of new editing groups
 */
const newEditingGroups = computed(() => {
    return Object.values(editingGroups.value).filter((g) => g.isNewGroup);
});

/**
 * Ensures an editing group exists and returns it
 * @param {string} groupId - The group ID to retrieve
 * @returns {EditGroup} The editing group
 * @throws {Error} When no editing group is found
 */
function ensureEditingGroup(groupId: string): EditGroup {
    const group = editingGroups.value[groupId];
    if (!group) {
        throw new Error(`No editing group found for ID: ${groupId}`);
    }
    return group;
}

/**
 * Checks if a variable or secret is optional
 * @param {string} name - Variable/secret name
 * @param {CredentialType} type - Type of credential (variable or secret)
 * @returns {boolean} True if the credential is optional
 */
function isVariableOptional(name: string, type: CredentialType): boolean {
    const definitions = type === "variable" ? props.serviceDefinition.variables : props.serviceDefinition.secrets;
    const definition = definitions.find((variable) => variable.name === name);
    return definition?.optional || false;
}

/**
 * Validates group data for completeness and uniqueness
 * @param {ServiceCredentialGroupPayload} groupData - Group data to validate
 * @returns {boolean} True if group data is valid
 */
function validateGroupData(groupData: ServiceCredentialGroupPayload): boolean {
    if (!groupData.name?.trim()) {
        return false;
    }

    const hasInvalidVariable = groupData.variables.some(
        (variable) => !variable.value && !isVariableOptional(variable.name, "variable"),
    );

    const hasInvalidSecret = groupData.secrets.some(
        (secret) => !secret.value && !isVariableOptional(secret.name, "secret"),
    );

    const hasDuplicateName = userServicesGroups.value.filter((group) => group.name === groupData.name).length > 1;

    return !hasInvalidVariable && !hasInvalidSecret && !hasDuplicateName;
}

/**
 * Determines if save button should be disabled for a group
 * @param {string} editingGroupKey - Key of the editing group
 * @returns {boolean} True if save button should be disabled
 */
const disableSaveButton = computed(() => {
    return (editingGroupKey: string): boolean => {
        const editGroup = editingGroups.value[editingGroupKey];
        if (!editGroup) {
            return true;
        }

        return isBusy.value || !validateGroupData(editGroup.groupPayload);
    };
});

/**
 * Generates a unique name for a new group
 * @param {string} template - Base name template
 * @param {ServiceCredentialGroupResponse[]} currentGroups - Existing groups
 * @returns {string} Unique group name
 */
function generateUniqueName(template: string, currentGroups: ServiceCredentialGroupResponse[]): string {
    let name = template;
    let counter = 1;
    while (currentGroups.some((group) => group.name === name)) {
        name = `${template} ${counter}`;
        counter++;
    }
    return name;
}

/**
 * Creates a new temporary group for editing
 * @returns {void}
 */
function createTemporaryGroup(): void {
    const editableGroup: ServiceCredentialGroupPayload = {
        name: generateUniqueName("new group", userServicesGroups.value),
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

/**
 * Prepares an existing group for editing
 * @param {string} groupId - ID of the group to edit
 * @returns {void}
 */
function editGroup(groupId: string): void {
    const groupToEdit = userServicesGroups.value.find((group) => group.id === groupId);

    if (!groupToEdit) {
        Toast.error(`Group not found: ${groupId}`);
        return;
    }

    const editableGroup: ServiceCredentialGroupPayload = {
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

/**
 * Discards changes to a group being edited
 * @param {string} groupId - ID of the group to discard changes for
 * @returns {void}
 */
function discardGroupChanges(groupId: string): void {
    const { [groupId]: _removedGroup, ...remainingGroups } = editingGroups.value;
    editingGroups.value = remainingGroups;
}

/**
 * Updates the current group selection
 * @param {ServiceCredentialGroupResponse} [selectedGroup] - Group to select, undefined to clear
 * @returns {void}
 */
function updateCurrentGroup(selectedGroup?: ServiceCredentialGroupResponse): void {
    emit("update-current-group", selectedGroup?.id);
}

/**
 * Clears the current group selection
 */
function onClearSelection() {
    updateCurrentGroup(undefined);
}

/**
 * Creates a new credential group
 * @param {EditGroup} editGroup - Group data to create
 * @returns {Promise<void>} Resolves when creation is complete
 * @throws {Error} When creation fails
 */
async function createGroup(editGroup: EditGroup): Promise<void> {
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

/**
 * Updates an existing credential group
 * @param {string} groupId - ID of the group to update
 * @returns {Promise<void>} Resolves when update is complete
 * @throws {Error} When update fails
 */
async function updateGroup(groupId: string): Promise<void> {
    try {
        const groupToUpdate = editingGroups.value[groupId];

        if (!groupToUpdate) {
            console.warn(`No group found for update: ${groupId}`);
            return;
        }

        saveButtonText.value = busyMessage.value;

        await saveUserCredentials(props.serviceDefinition, groupId, groupToUpdate.groupPayload);

        discardGroupChanges(groupId);

        Toast.success("Credentials group updated successfully");
    } catch (error) {
        console.error("Error saving credentials:", error);
        Toast.error(`${errorMessageAsString(error)}`);
    } finally {
        saveButtonText.value = "Save";
    }
}

/**
 * Deletes a credential group after confirmation
 * @param {ServiceCredentialGroupResponse} groupToDelete - Group to delete
 * @return {Promise<void>} Resolves when deletion is complete
 * @throws {Error} When deletion fails
 */
async function deleteGroup(groupToDelete: ServiceCredentialGroupResponse): Promise<void> {
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

/**
 * Generates primary action configuration for existing credential groups
 * @param {ServiceCredentialGroupResponse} groupData - The credential group
 * @returns {CardAction[]} Array of action configurations
 */
const primaryActions = computed(() => (groupData: ServiceCredentialGroupResponse): CardAction[] => {
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

/**
 * Generates primary action configuration for new credential groups
 * @param {EditGroup} editGroup - The editing group
 * @returns {CardAction[]} Array of action configurations
 */
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

/**
 * Generates indicator configuration for credential groups
 * @param {ServiceCredentialGroupResponse} group - The credential group
 * @returns {CardIndicator[]} Array of indicator configurations
 */
const groupIndicators = computed(() => (group: ServiceCredentialGroupResponse): CardIndicator[] => {
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
                    :primary-actions="primaryActions(usg)"
                    :update-time="usg.update_time">
                    <template v-if="editingGroups[usg.id]" v-slot:description>
                        <CredentialsGroupForm
                            :group-data="ensureEditingGroup(usg.id)"
                            :service-definition="props.serviceDefinition" />
                    </template>
                </GCard>
            </div>
        </BCollapse>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

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
