<script setup lang="ts">
import { type ConcreteObjectStoreModel, type SelectableObjectStore } from "@/api";

import ObjectStoreSelectButton from "@/components/ObjectStore/ObjectStoreSelectButton.vue";
import ObjectStoreSelectButtonDescribePopover from "@/components/ObjectStore/ObjectStoreSelectButtonDescribePopover.vue";

interface RelocateProps {
    fromObjectStore: ConcreteObjectStoreModel;
    targetObjectStores: SelectableObjectStore[];
}

defineProps<RelocateProps>();

const emit = defineEmits<{
    (e: "relocate", value: string): void;
    (e: "closeModal"): void;
}>();

function relocate(objectStoreId: string) {
    emit("relocate", objectStoreId);
}

const fromWhat = "This dataset location is";
const toWhat = "This dataset will be relocated to";
</script>

<template>
    <div>
        <p>Currently the dataset is located in:</p>
        <b-button-group vertical size="lg" class="select-button-group">
            <ObjectStoreSelectButton
                :key="fromObjectStore.object_store_id"
                id-prefix="swap-target"
                class="swap-target-object-store-select-button"
                variant="info"
                :object-store="fromObjectStore"
                @click="emit('closeModal')" />
        </b-button-group>
        <p class="relocate-to">Select new storage location for the dataset:</p>
        <b-button-group vertical size="lg" class="select-button-group">
            <ObjectStoreSelectButton
                v-for="objectStore in targetObjectStores"
                :key="objectStore.object_store_id"
                id-prefix="swap-target"
                class="swap-target-object-store-select-button"
                variant="outline-primary"
                :object-store="objectStore"
                @click="relocate(objectStore.object_store_id)" />
        </b-button-group>
        <ObjectStoreSelectButtonDescribePopover
            id-prefix="swap-target"
            :what="fromWhat"
            :object-store="fromObjectStore" />
        <ObjectStoreSelectButtonDescribePopover
            v-for="objectStore in targetObjectStores"
            :key="objectStore.object_store_id"
            id-prefix="swap-target"
            :what="toWhat"
            :object-store="objectStore" />
    </div>
</template>

<style scoped>
.select-button-group {
    display: block;
    margin: auto;
    width: 400px;
}
.relocate-to {
    margin-top: 2em;
}
</style>
