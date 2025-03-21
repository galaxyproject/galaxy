<script setup lang="ts">
import { type ConcreteObjectStoreModel } from "@/api";

import ObjectStoreSelectButton from "@/components/ObjectStore/ObjectStoreSelectButton.vue";
import ObjectStoreSelectButtonDescribePopover from "@/components/ObjectStore/ObjectStoreSelectButtonDescribePopover.vue";

interface RelocateProps {
    objectStores: ConcreteObjectStoreModel[];
}

defineProps<RelocateProps>();

const emit = defineEmits<{
    (e: "select", value: string | null): void;
}>();

const toWhat = "数据集将被筛选为存储在";
</script>

<template>
    <div>
        <p>选择存储源进行筛选</p>
        <b-button-group vertical size="lg" class="select-button-group">
            <ObjectStoreSelectButton
                v-for="objectStore in objectStores"
                :key="objectStore.object_store_id"
                id-prefix="filter-target"
                class="filter-target-object-store-select-button"
                variant="outline-primary"
                :object-store="objectStore"
                @click="emit('select', objectStore.object_store_id ?? null)" />
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
