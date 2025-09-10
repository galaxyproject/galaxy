<script setup lang="ts">
import { faKey, faPencilAlt, faTrash, faWrench } from "@fortawesome/free-solid-svg-icons";
import { BModal } from "bootstrap-vue";
import { faCheck } from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { ServiceCredentialsDefinition, ServiceGroupPayload } from "@/api/users";
import type { CardAction, CardBadge, TitleIcon } from "@/components/Common/GCard.types";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserToolCredentials } from "@/composables/userToolCredentials";
import { useToolStore } from "@/stores/toolStore";
import {
    SECRET_PLACEHOLDER,
    type ServiceCredentialsGroupDetails,
    useUserToolsServiceCredentialsStore,
} from "@/stores/userToolsServiceCredentialsStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GCard from "@/components/Common/GCard.vue";
import CredentialsGroupForm from "@/components/User/Credentials/CredentialsGroupForm.vue";

interface EditData {
    sourceId: string;
    sourceVersion: string;
    groupData: {
        groupId: string;
        groupPayload: ServiceGroupPayload;
        isNewGroup: boolean;
    };
    serviceDefinition: ServiceCredentialsDefinition;
}

interface Props {
    serviceGroups: ServiceCredentialsGroupDetails[];
}

const props = defineProps<Props>();

const { confirm } = useConfirmDialog();

const { getToolNameById } = useToolStore();

const userToolsServiceCredentialsStore = useUserToolsServiceCredentialsStore();
const { userToolsServicesCurrentGroupIds } = storeToRefs(userToolsServiceCredentialsStore);

const showModal = ref(false);
const saveButtonText = ref("Save Changes");
const editData = ref<EditData>();

const cardTitleIcon: TitleIcon = { icon: faKey, size: "sm" };

const cardTitle = computed(() => (group: ServiceCredentialsGroupDetails) => {
    return `${group.serviceDefinition.name} (v${group.serviceDefinition.version}) - ${group.name}`;
});
const isGroupInUse = computed(() => (group: ServiceCredentialsGroupDetails) => {
    const userToolKey = userToolsServiceCredentialsStore.getUserToolKey(group.sourceId, group.sourceVersion);
    const userToolService = userToolsServicesCurrentGroupIds.value[userToolKey];
    for (const groupId of Object.values(userToolService || {})) {
        if (groupId === group.id) {
            return true;
        }
    }
    return false;
});

async function deleteGroup(groupToDelete: ServiceCredentialsGroupDetails) {
    let message = `Are you sure you want to delete the credentials group "${groupToDelete.name}"?`;

    if (isGroupInUse.value(groupToDelete)) {
        message = message.concat(` This group is currently in use by '${getToolNameById(groupToDelete.sourceId)}'.`);
    }

    const confirmed = await confirm(message, {
        title: "Delete credentials group",
        okTitle: "Delete group",
        okVariant: "danger",
        cancelVariant: "outline-primary",
        centered: true,
    });

    if (confirmed && groupToDelete) {
        const { deleteCredentialsGroup } = useUserToolCredentials(groupToDelete.sourceId, groupToDelete.sourceVersion);

        try {
            await deleteCredentialsGroup(groupToDelete.serviceDefinition, groupToDelete.id);
            Toast.success("Credentials group deleted successfully");
        } catch (error) {
            console.error("Error deleting group:", error);
            Toast.error(`Error deleting group: ${errorMessageAsString(error)}`);
        }
    }
}

function editGroup(group: ServiceCredentialsGroupDetails) {
    editData.value = {
        sourceId: group.sourceId,
        sourceVersion: group.sourceVersion,
        groupData: {
            groupId: group.id,
            groupPayload: {
                name: group.name,
                secrets: group.secrets.map((secret) => ({
                    name: secret.name,
                    value: secret.is_set ? SECRET_PLACEHOLDER : "",
                })),
                variables: group.variables.map((variable) => ({
                    name: variable.name,
                    value: variable.value,
                })),
            },
            isNewGroup: false,
        },
        serviceDefinition: group.serviceDefinition,
    };

    showModal.value = true;
}

async function onSaveChanges() {
    if (!editData.value) {
        return;
    }

    const { busyMessage } = storeToRefs(userToolsServiceCredentialsStore);
    const { saveUserCredentials } = useUserToolCredentials(editData.value.sourceId, editData.value.sourceVersion);

    try {
        const groupToUpdate = editData.value;

        if (!groupToUpdate) {
            console.warn(`No group found for update`);
            return;
        }

        saveButtonText.value = busyMessage.value;

        await saveUserCredentials(groupToUpdate.groupData.groupId, groupToUpdate.groupData.groupPayload);

        Toast.success("Credentials group updated successfully");

        editData.value = undefined;
    } catch (error) {
        console.error("Error saving credentials:", error);
        Toast.error(`Error saving credentials: ${errorMessageAsString(error)}`);
    } finally {
        saveButtonText.value = "Save";
    }
}

function getBadgesFor(group: ServiceCredentialsGroupDetails): CardBadge[] {
    const badges: CardBadge[] = [
        {
            id: `tool-${group.sourceId}`,
            icon: faWrench,
            title: "This tool is using this credentials group. Click to view.",
            label: getToolNameById(group.sourceId),
            to: `/root?tool_id=${group.sourceId}&tool_version=${group.sourceVersion}`,
        },
        {
            id: `in-use-${group.id}`,
            icon: faCheck,
            title: "This group is currently in use.",
            label: "In Use",
            variant: "success",
            visible: isGroupInUse.value(group),
        },
    ];
    return badges;
}

function getPrimaryActions(group: ServiceCredentialsGroupDetails): CardAction[] {
    const primaryActions: CardAction[] = [
        {
            id: `delete-${group.id}`,
            label: "Delete",
            title: "Delete this group",
            icon: faTrash,
            variant: "outline-danger",
            handler: () => deleteGroup(group),
        },
        {
            id: `edit-${group.id}`,
            label: "Edit",
            title: "Edit this group",
            icon: faPencilAlt,
            variant: "outline-info",
            handler: () => editGroup(group),
        },
    ];
    return primaryActions;
}
</script>

<template>
    <div>
        <GCard
            v-for="group in props.serviceGroups"
            :id="`group-${group.id}-${group.name}`"
            :key="`group-${group.id}-${group.name}`"
            :title="cardTitle(group)"
            :title-icon="cardTitleIcon"
            :description="group.serviceDefinition.description"
            :badges="getBadgesFor(group)"
            :published="isGroupInUse(group)"
            :primary-actions="getPrimaryActions(group)">
        </GCard>

        <BModal
            v-model="showModal"
            visible
            centered
            scrollable
            no-close-on-backdrop
            no-close-on-esc
            button-size="md"
            size="lg"
            body-class="edit-credentials-body"
            :title="`Edit Credentials Group - ${editData?.groupData.groupPayload.name}`"
            :ok-title="saveButtonText"
            cancel-title="Close"
            cancel-variant="outline-danger"
            @ok="onSaveChanges">
            <CredentialsGroupForm
                v-if="editData"
                :group-data="editData.groupData"
                :service-definition="editData.serviceDefinition" />
        </BModal>
    </div>
</template>
