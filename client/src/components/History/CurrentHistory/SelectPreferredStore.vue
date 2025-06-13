<script setup lang="ts">
import axios from "axios";
import { computed, ref } from "vue";

import { getPermissions, isHistoryPrivate, makePrivate, type PermissionsResponse } from "@/components/History/services";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import SelectObjectStore from "@/components/ObjectStore/SelectObjectStore.vue";

const props = defineProps({
    userPreferredObjectStoreId: {
        type: String,
        default: null,
    },
    history: {
        type: Object,
        required: true,
    },
});

const error = ref<string | null>(null);
const selectedObjectStoreId = ref(props.history.preferred_object_store_id);

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
                    "Your history is set to create sharable datasets, but the target storage is private. Change the history configuration so new datasets are private by default?"
                )
            ) {
                try {
                    await makePrivate(props.history.id, permissionResponse);
                } catch {
                    error.value = "Failed to update default permissions for history.";
                }
            }
        }
    }

    const payload = { preferred_object_store_id: preferredObjectStoreId };
    const url = prependPath(`api/histories/${props.history.id}`);
    try {
        await axios.put(url, payload);
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
    selectedObjectStoreId.value = preferredObjectStoreId;
    emit("updated", preferredObjectStoreId);
}
</script>
<template>
    <SelectObjectStore
        :parent-error="error || undefined"
        :for-what="newDatasetsDescription"
        :selected-object-store-id="selectedObjectStoreId"
        :default-option-title="defaultOptionTitle"
        :default-option-description="defaultOptionDescription"
        @onSubmit="handleSubmit" />
</template>
