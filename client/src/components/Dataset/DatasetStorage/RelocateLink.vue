<script setup lang="ts">
import { faExchangeAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { DatasetStorageDetails, UserConcreteObjectStoreModel } from "@/api";
import { updateObjectStore } from "@/api/objectStores";
import { useObjectStoreStore } from "@/stores/objectStoreStore";
import { errorMessageAsString } from "@/utils/simple-error.js";

import RelocateDialog from "./RelocateDialog.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import LoadingOverlay from "@/components/Common/LoadingOverlay.vue";

interface RelocateLinkProps {
    datasetStorageDetails: DatasetStorageDetails;
    datasetId: string;
}

const props = defineProps<RelocateLinkProps>();

const showModal = ref(false);
const relocating = ref(false);
const relocationError = ref<string | null>(null);

const store = useObjectStoreStore();
const { loading, selectableObjectStores } = storeToRefs(store);

const currentObjectStore = computed<UserConcreteObjectStoreModel | null>(() => {
    const isLoadedVal = !loading.value;
    const objectStores = selectableObjectStores.value;
    const currentObjectStoreId = props.datasetStorageDetails.object_store_id;

    if (!isLoadedVal) {
        return null;
    }
    if (!objectStores) {
        return null;
    }
    const filtered = objectStores.filter(
        (objectStore: UserConcreteObjectStoreModel) => objectStore.object_store_id == currentObjectStoreId,
    );
    return filtered.length > 0 ? filtered[0]! : null;
});

const validTargets = computed<UserConcreteObjectStoreModel[]>(() => {
    const isLoadedVal = !loading.value;
    const objectStores = selectableObjectStores.value;
    const currentObjectStoreId = props.datasetStorageDetails.object_store_id;

    if (!isLoadedVal) {
        return [];
    }
    if (!objectStores) {
        return [];
    }
    if (!currentObjectStore.value) {
        return [];
    }
    const currentDevice = currentObjectStore.value.device;
    if (!currentDevice) {
        return [];
    }
    return objectStores.filter(
        (objectStore: UserConcreteObjectStoreModel) =>
            objectStore.device == currentDevice &&
            objectStore.object_store_id &&
            objectStore.object_store_id != currentObjectStoreId,
    );
});

const relocatable = computed(() => {
    return validTargets.value.length > 0;
});

const emit = defineEmits<{
    (e: "relocated"): void;
}>();

async function relocate(objectStoreId: string) {
    relocating.value = true;
    relocationError.value = null;
    try {
        await updateObjectStore(props.datasetId, objectStoreId);
        emit("relocated");
    } catch (err) {
        relocationError.value = errorMessageAsString(err, "Failed to relocate dataset.");
    } finally {
        relocating.value = false;
    }
}
</script>

<template>
    <span class="storage-relocate-link d-flex justify-content-center">
        <GModal v-if="currentObjectStore" size="small" :show.sync="showModal" title="Relocate Dataset">
            <LoadingOverlay v-if="relocating" />
            <GAlert v-if="relocationError">
                {{ relocationError }}
            </GAlert>
            <RelocateDialog
                :from-object-store="currentObjectStore"
                :target-object-stores="validTargets"
                @relocate="relocate" />
        </GModal>
        <GButton v-if="relocatable" pill @click="showModal = true">
            <FontAwesomeIcon :icon="faExchangeAlt" />
            Relocate Dataset
        </GButton>
    </span>
</template>
