<script setup lang="ts">
import { type ConcreteObjectStoreModel } from "@/api";

import ObjectStoreSelectButton from "@/components/ObjectStore/ObjectStoreSelectButton.vue";
import ObjectStoreSelectButtonDescribePopover from "@/components/ObjectStore/ObjectStoreSelectButtonDescribePopover.vue";

interface RelocateProps {
    objectStores: ConcreteObjectStoreModel[];
}

defineProps<RelocateProps>();

const emit = defineEmits<{
    (e: "select", value: string): void;
}>();

const toWhat = "Datasets will be filtered to those stored in";
</script>

<template>
    <div>
        <p>Select a storage source to filter by</p>
        <b-button-group vertical size="lg" class="select-button-group">
            <ObjectStoreSelectButton
                v-for="objectStore in objectStores"
                :key="objectStore.object_store_id"
                id-prefix="filter-target"
                class="filter-target-object-store-select-button"
                variant="outline-primary"
                :object-store="objectStore"
                @click="emit('select', objectStore.object_store_id)" />
        </b-button-group>
        <ObjectStoreSelectButtonDescribePopover
            v-for="objectStore in objectStores"
            :key="objectStore.object_store_id"
            id-prefix="filter-target"
            :what="toWhat"
            :object-store="objectStore" />
        <p></p>
    </div>
</template>

<style scoped>
.select-button-group {
    display: block;
    margin: auto;
    width: 400px;
}
</style>
