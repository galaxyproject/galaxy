<script setup lang="ts">
import { ConcreteObjectStoreModel } from "@/api";

import ObjectStoreSelectButton from "@/components/ObjectStore/ObjectStoreSelectButton.vue";
import ObjectStoreSelectButtonDescribePopover from "@/components/ObjectStore/ObjectStoreSelectButtonDescribePopover.vue";

interface RelocateProps {
    fromObjectStore: ConcreteObjectStoreModel;
    targetObjectStores: ConcreteObjectStoreModel[];
}

defineProps<RelocateProps>();

const emit = defineEmits<{
    (e: "relocate", value: string): void;
}>();

const fromWhat = "This dataset location in a";
const toWhat = "This dataset will be relocated to";
</script>

<template>
    <div>
        <p>Relocate the dataset's current object store of:</p>
        <b-button-group vertical size="lg" class="select-button-group">
            <ObjectStoreSelectButton
                :key="fromObjectStore.object_store_id"
                id-prefix="swap-target"
                class="swap-target-object-store-select-button"
                variant="info"
                :object-store="fromObjectStore" />
        </b-button-group>
        <p>Select a new object store below to relocate the dataset</p>
        <b-button-group vertical size="lg" class="select-button-group">
            <ObjectStoreSelectButton
                v-for="objectStore in targetObjectStores"
                :key="objectStore.object_store_id"
                id-prefix="swap-target"
                class="swap-target-object-store-select-button"
                variant="outline-primary"
                :object-store="objectStore"
                @click="emit('relocate', objectStore.object_store_id)" />
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
</style>
