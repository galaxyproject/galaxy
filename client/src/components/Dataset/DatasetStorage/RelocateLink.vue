<script setup lang="ts">
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { type ConcreteObjectStoreModel, type DatasetStorageDetails } from "@/api";
import { updateObjectStore } from "@/api/objectStores";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import RelocateDialog from "./RelocateDialog.vue";
import SelectModal from "./SelectModal.vue";

interface RelocateLinkProps {
    datasetStorageDetails: DatasetStorageDetails;
    datasetId: string;
}

const props = defineProps<RelocateLinkProps>();

const showModal = ref(false);

const store = useObjectStoreStore();
const { isLoaded, selectableObjectStores } = storeToRefs(store);

const currentObjectStore = computed<ConcreteObjectStoreModel | null>(() => {
    const isLoadedVal = isLoaded.value;
    const objectStores = selectableObjectStores.value;
    const currentObjectStoreId = props.datasetStorageDetails.object_store_id;

    if (!isLoadedVal) {
        return null;
    }
    if (!objectStores) {
        return null;
    }
    const filtered: ConcreteObjectStoreModel[] = objectStores.filter(
        (objectStore) => objectStore.object_store_id == currentObjectStoreId
    );
    return filtered && filtered.length > 0 ? (filtered[0] as ConcreteObjectStoreModel) : null;
});

const validTargets = computed<ConcreteObjectStoreModel[]>(() => {
    const isLoadedVal = isLoaded.value;
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
    const validTargets: ConcreteObjectStoreModel[] = objectStores.filter(
        (objectStore) =>
            objectStore.device == currentDevice &&
            objectStore.object_store_id &&
            objectStore.object_store_id != currentObjectStoreId
    );
    return validTargets as ConcreteObjectStoreModel[];
});

const relocatable = computed(() => {
    return validTargets.value.length > 0;
});

const emit = defineEmits<{
    (e: "relocated"): void;
}>();

function closeModal() {
    showModal.value = false;
}

async function relocate(objectStoreId: string) {
    try {
        await updateObjectStore(props.datasetId, objectStoreId);
        emit("relocated");
    } catch (err) {
        console.log(err);
    } finally {
        showModal.value = false;
    }
}
</script>

<template>
    <span class="storage-relocate-link">
        <SelectModal v-if="currentObjectStore" v-model="showModal" title="Relocate Dataset">
            <RelocateDialog
                :from-object-store="currentObjectStore"
                :target-object-stores="validTargets"
                @relocate="relocate"
                @closeModal="closeModal" />
        </SelectModal>
        <BButton v-if="relocatable" @click="showModal = true">Relocate Dataset</BButton>
    </span>
</template>
