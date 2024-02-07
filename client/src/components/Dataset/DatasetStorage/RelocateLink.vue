<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { ConcreteObjectStoreModel, DatasetStorageDetails } from "@/api";
import { updateObjectStore } from "@/api/objectStores";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import RelocateModal from "./RelocateModal.vue";

interface RelocateLinkProps {
    datasetStorageDetails: DatasetStorageDetails;
    datasetId: string;
}

const props = defineProps<RelocateLinkProps>();

const relocateModal = ref<InstanceType<typeof RelocateModal> | null>(null);

function showRelocateDialog() {
    // This should work - does it work in proper Vue 3 or something?
    // https://vuejs.org/guide/typescript/composition-api.html#typing-component-template-refs
    // @ts-ignore
    relocateModal.value?.showModal();
}

function hideRelocateDialog() {
    // This should work - does it work in proper Vue 3 or something?
    // https://vuejs.org/guide/typescript/composition-api.html#typing-component-template-refs
    // @ts-ignore
    relocateModal.value?.hideModal();
}

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
        (objectStore) => objectStore.device == currentDevice && objectStore.object_store_id != currentObjectStoreId
    );
    return validTargets as ConcreteObjectStoreModel[];
});

const relocatable = computed(() => {
    return validTargets.value.length > 0;
});

const emit = defineEmits<{
    (e: "relocated"): void;
}>();

async function relocate(objectStoreId: string) {
    try {
        await updateObjectStore(props.datasetId, objectStoreId);
        hideRelocateDialog();
        emit("relocated");
    } catch (err) {
        console.log(err);
    }
}
</script>

<template>
    <span class="storage-relocate-link">
        <RelocateModal
            v-if="currentObjectStore"
            ref="relocateModal"
            :from-object-store="currentObjectStore"
            :target-object-stores="validTargets"
            @relocate="relocate" />
        <b-link v-if="relocatable" href="#" @click="showRelocateDialog">(relocate)</b-link>
    </span>
</template>
