<script setup lang="ts">
import axios from "axios";
import { BModal, type BvModalEvent } from "bootstrap-vue";
import { computed, type PropType, ref } from "vue";

import { getPermissions, isHistoryPrivate, makePrivate, type PermissionsResponse } from "@/components/History/services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useStorageLocationConfiguration } from "@/composables/storageLocation";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import SelectObjectStore from "@/components/ObjectStore/SelectObjectStore.vue";

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
    showModal: {
        type: Boolean,
        default: false,
    },
});

const { confirm } = useConfirmDialog();

const error = ref();

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

const emit = defineEmits<{
    (e: "close"): void;
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
                    okTitle: "Private new datasets",
                    cancelTitle: "Keep datasets public",
                    cancelVariant: "outline-primary",
                },
            );

            if (confirmed) {
                try {
                    await makePrivate(props.history.id, permissionResponse);
                } catch {
                    error.value = "Failed to update default permissions for history.";
                    throw new Error();
                }
            }
        }
    }

    const payload = { preferred_object_store_id: preferredObjectStoreId };
    const url = prependPath(`api/histories/${props.history.id}`);
    try {
        await axios.put(url, payload);
        emit("updated", preferredObjectStoreId);
    } catch (e) {
        error.value = errorMessageAsString(e);
        throw new Error();
    }
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

async function modalOk(event: BvModalEvent) {
    event?.preventDefault();

    try {
        await handleSubmit(currentSelectedStoreId.value, currentSelectedStorePrivate.value);

        reset();
        emit("close");
    } catch (_e) {
        // pass
    }
}

function reset() {
    currentSelectedStoreId.value = props.preferredObjectStoreId;
    currentSelectedStorePrivate.value = false;
    error.value = null;
}
</script>

<template>
    <BModal
        :visible="props.showModal"
        centered
        scrollable
        size="lg"
        :title="storageLocationTitle"
        title-class="h-sm"
        title-tag="h3"
        ok-title="Change Storage Location"
        cancel-variant="outline-primary"
        :ok-disabled="currentSelectedStoreId === props.preferredObjectStoreId"
        :no-close-on-backdrop="currentSelectedStoreId !== props.preferredObjectStoreId"
        :no-close-on-esc="currentSelectedStoreId !== props.preferredObjectStoreId"
        @cancel="reset"
        @change="emit('close')"
        @close="reset"
        @ok="modalOk">
        <SelectObjectStore
            :show-sub-setting="props.showSubSetting"
            :parent-error="error"
            :for-what="newDatasetsDescription"
            :selected-object-store-id="currentSelectedStoreId"
            :default-option-title="defaultOptionTitle"
            :default-option-description="defaultOptionDescription"
            @onSubmit="selectionChanged" />
    </BModal>
</template>
