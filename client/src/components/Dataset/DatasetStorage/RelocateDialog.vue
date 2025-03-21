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

const fromWhat = "该数据集的位置是";
const toWhat = "该数据集将被重新定位到";
</script>

<template>
    <div>
        <p>当前数据集位于：</p>
        <b-button-group vertical size="lg" class="select-button-group">
            <ObjectStoreSelectButton
                :key="fromObjectStore.object_store_id"
                id-prefix="swap-target"
                class="swap-target-object-store-select-button"
                variant="info"
                :object-store="fromObjectStore"
                @click="emit('closeModal')" />
        </b-button-group>
        <p class="relocate-to">请选择数据集的新存储位置：</p>
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
