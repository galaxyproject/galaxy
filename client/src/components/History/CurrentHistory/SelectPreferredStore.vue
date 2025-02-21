<script setup lang="ts">
import axios from "axios";
import { BModal, type BvModalEvent } from "bootstrap-vue";
import { computed, type PropType, ref } from "vue";

import { getPermissions, isHistoryPrivate, makePrivate, type PermissionsResponse } from "@/components/History/services";
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
});

const error = ref<string | null>(null);

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
    (e: "updated", id: string | null): void;
}>();

async function handleSubmit(preferredObjectStoreId: string | null, isPrivate: boolean) {
    if (isPrivate) {
        const { data } = await getPermissions(props.history.id);
        const permissionResponse = data as PermissionsResponse;
        const historyPrivate = await isHistoryPrivate(permissionResponse);
        if (!historyPrivate) {
            if (
                confirm(
                    "Your history is set to create sharable datasets, but the target storage location is private. Change the history configuration so new datasets are private by default?"
                )
            ) {
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

const modalShown = ref(false);

function showModal() {
    modalShown.value = true;
}

const currentSelectedStoreId = ref<string | null>(props.preferredObjectStoreId);
const currentSelectedStorePrivate = ref(false);

function selectionChanged(preferredObjectStoreId: string | null, isPrivate: boolean) {
    currentSelectedStoreId.value = preferredObjectStoreId;
    currentSelectedStorePrivate.value = isPrivate;
}

async function modalOk(event: BvModalEvent) {
    if (currentSelectedStoreId.value !== props.preferredObjectStoreId) {
        event.preventDefault();

        try {
            await handleSubmit(currentSelectedStoreId.value, currentSelectedStorePrivate.value);
            modalShown.value = false;
        } catch (_e) {
            // pass
        }
    }
}

function reset() {
    currentSelectedStoreId.value = props.preferredObjectStoreId;
    currentSelectedStorePrivate.value = false;
}

defineExpose({
    showModal,
});
</script>

<template>
    <BModal
        v-model="modalShown"
        :title="storageLocationTitle"
        title-tag="h2"
        title-class="h-sm"
        @ok="modalOk"
        @cancel="reset"
        @close="reset">
        <SelectObjectStore
            :parent-error="error || undefined"
            :for-what="newDatasetsDescription"
            :selected-object-store-id="currentSelectedStoreId"
            :default-option-title="defaultOptionTitle"
            :default-option-description="defaultOptionDescription"
            @onSubmit="selectionChanged" />
    </BModal>
</template>
