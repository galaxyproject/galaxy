<script setup lang="ts">
import { computed } from "vue";

import { type ConcreteObjectStoreModel } from "@/api";

import DescribeObjectStore from "./DescribeObjectStore.vue";
import ObjectStoreSelectButtonPopover from "./ObjectStoreSelectButtonPopover.vue";

interface ObjectStoreSelectButtonPopoverDescribeProps {
    idPrefix: string;
    what: string;
    objectStore: ConcreteObjectStoreModel;
}

const props = defineProps<ObjectStoreSelectButtonPopoverDescribeProps>();

const target = computed(() => {
    return `${props.idPrefix}-object-store-button-${props.objectStore.object_store_id}`;
});
const title = computed(() => {
    return props.objectStore.name;
});
</script>

<template>
    <ObjectStoreSelectButtonPopover :target="target" :title="title">
        <DescribeObjectStore :what="what" :storage-info="objectStore"> </DescribeObjectStore>
    </ObjectStoreSelectButtonPopover>
</template>
