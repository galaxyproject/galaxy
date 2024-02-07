<script setup lang="ts">
import { ConcreteObjectStoreModel } from "@/api";

import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";
import ObjectStoreSelectButton from "@/components/ObjectStore/ObjectStoreSelectButton.vue";
import ObjectStoreSelectButtonPopover from "@/components/ObjectStore/ObjectStoreSelectButtonPopover.vue";

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
                :id="`swap-target-object-store-button-${fromObjectStore.object_store_id}`"
                :key="fromObjectStore.object_store_id"
                class="swap-target-object-store-select-button"
                variant="info"
                :object-store="fromObjectStore" />
        </b-button-group>
        <p>Select a new object store below to relocate the dataset</p>
        <b-button-group vertical size="lg" class="select-button-group">
            <ObjectStoreSelectButton
                v-for="objectStore in targetObjectStores"
                :id="`swap-target-object-store-button-${objectStore.object_store_id}`"
                :key="objectStore.object_store_id"
                class="swap-target-object-store-select-button"
                :data-object-store-id="objectStore.object_store_id"
                variant="outline-primary"
                :objectStore="objectStore"
                @click="emit('relocate', objectStore.object_store_id)" />
        </b-button-group>
        <ObjectStoreSelectButtonPopover
            :target="`swap-target-object-store-button-${fromObjectStore.object_store_id}`"
            :title="fromObjectStore.name">
            <DescribeObjectStore :what="fromWhat" :storage-info="fromObjectStore"> </DescribeObjectStore>
        </ObjectStoreSelectButtonPopover>
        <ObjectStoreSelectButtonPopover
            v-for="objectStore in targetObjectStores"
            :key="objectStore.object_store_id"
            :target="`swap-target-object-store-button-${objectStore.object_store_id}`"
            :title="objectStore.name">
            <DescribeObjectStore :what="toWhat" :storage-info="objectStore"> </DescribeObjectStore>
        </ObjectStoreSelectButtonPopover>
    </div>
</template>

<style scoped>
.select-button-group {
    display: block;
    margin: auto;
    width: 400px;
}
</style>
