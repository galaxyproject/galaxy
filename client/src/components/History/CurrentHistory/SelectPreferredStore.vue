<script setup lang="ts">
import axios from "axios";
import { computed, type PropType, ref } from "vue";

import { getPermissions, isHistoryPrivate, makePrivate, type PermissionsResponse } from "@/components/History/services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useStorageLocationConfiguration } from "@/composables/storageLocation";
import { useToast } from "@/composables/toast";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import GModal from "@/components/BaseComponents/GModal.vue";
import SelectObjectStore from "@/components/ObjectStore/SelectObjectStore.vue";

const Toast = useToast();

const props = defineProps({
    userPreferredObjectStoreId: {
        type: String as PropType<string | null>,
        default: null,
    },
    preferredObjectStoreId: {
        type: String as PropType<string | null>,
        default: null,
    },
    history: {
        type: Object,
        required: true,
    },
    showSubSetting: {
        type: Boolean,
        default: false,
    },
    show: {
        type: Boolean,
        required: true,
    },
});

const { confirm } = useConfirmDialog();

const newDatasetsDescription = "New dataset outputs from tools and workflows executed in this history";
const galaxySelectionDefaultTitle = "Use Galaxy Defaults";
const galaxySelectionDefaultDescription =
    "Selecting this will reset Galaxy to default behaviors configured by your Galaxy administrator.";
const userSelectionDefaultTitle = "Use Your User Preference Defaults";
const userSelectionDefaultDescription =
    "Selecting this will cause the history to not set a default and to fallback to your user preference defined default.";

const defaultOptionTitle = computed(() => {
    if (props.userPreferredObjectStoreId) {
        return userSelectionDefaultTitle;
    } else {
        return galaxySelectionDefaultTitle;
    }
});

const defaultOptionDescription = computed(() => {
    if (props.userPreferredObjectStoreId) {
        return userSelectionDefaultDescription;
    } else {
        return galaxySelectionDefaultDescription;
    }
});

/** Computed toggle that handles showing and hiding the modal */
const localShowToggle = computed({
    get: () => props.show,
    set: (value: boolean) => {
        emit("update:show", value);
    },
});

const emit = defineEmits<{
    (e: "update:show", value: boolean): void;
    (e: "updated", id: string | null): void;
}>();

async function handleSubmit(preferredObjectStoreId: string | null, isPrivate: boolean) {
    if (isPrivate) {
        const { data } = await getPermissions(props.history.id);
        const permissionResponse = data as PermissionsResponse;
        const historyPrivate = await isHistoryPrivate(permissionResponse);

        if (!historyPrivate) {
            const confirmed = await confirm(
                "Your history is set to create sharable datasets, but the target storage location is private. Change the history configuration so new datasets are private by default?",
                {
                    okText: "Private new datasets",
                    cancelText: "Keep datasets public",
                },
            );

            if (confirmed) {
                try {
                    await makePrivate(props.history.id, permissionResponse);
                } catch (e) {
                    throw new Error(errorMessageAsString(e || "Failed to update default permissions for history."));
                }
            }
        }
    }

    const payload = { preferred_object_store_id: preferredObjectStoreId };
    const url = prependPath(`api/histories/${props.history.id}`);

    await axios.put(url, payload);
    emit("updated", preferredObjectStoreId);
}

const { isOnlyPreference } = useStorageLocationConfiguration();

const storageLocationTitle = computed(() => {
    if (isOnlyPreference.value) {
        return "History Preferred Storage Location";
    } else {
        return "History Storage Location";
    }
});

const currentSelectedStoreId = ref<string | null>(props.preferredObjectStoreId);
const currentSelectedStorePrivate = ref(false);

function selectionChanged(preferredObjectStoreId: string | null, isPrivate: boolean) {
    currentSelectedStoreId.value = preferredObjectStoreId;
    currentSelectedStorePrivate.value = isPrivate;
}

async function modalOk() {
    try {
        await handleSubmit(currentSelectedStoreId.value, currentSelectedStorePrivate.value);
        reset();
        localShowToggle.value = false;
    } catch (e) {
        Toast.error(errorMessageAsString(e), "Failed to update history storage location");
    }
}

function reset() {
    currentSelectedStoreId.value = props.preferredObjectStoreId;
    currentSelectedStorePrivate.value = false;
}
</script>

<template>
    <GModal
        id="modal-select-history-storage-location"
        :show.sync="localShowToggle"
        size="small"
        :title="storageLocationTitle"
        ok-text="Change Storage Location"
        class="modal-select-history-storage-location"
        :ok-disabled="currentSelectedStoreId === props.preferredObjectStoreId"
        confirm
        :close-on-ok="false"
        @cancel="reset"
        @ok="modalOk">
        <SelectObjectStore
            :show-sub-setting="props.showSubSetting"
            :for-what="newDatasetsDescription"
            :selected-object-store-id="currentSelectedStoreId"
            :default-option-title="defaultOptionTitle"
            :default-option-description="defaultOptionDescription"
            @onSubmit="selectionChanged" />
    </GModal>
</template>
