<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";

import { useAdminExtensionsStore } from "@/stores/adminExtensionsStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import CenterFrame from "@/entry/analysis/modules/CenterFrame.vue";

const props = defineProps<{
    extensionId: string;
    itemId: string;
}>();

const adminExtensionsStore = useAdminExtensionsStore();
const { loaded, errorMessage } = storeToRefs(adminExtensionsStore);

onMounted(() => {
    adminExtensionsStore.loadExtensions();
});

const item = computed(() => adminExtensionsStore.getItem(props.extensionId, props.itemId));
const frameId = computed(() => `admin-extension-${props.extensionId}-${props.itemId}`);
</script>

<template>
    <div class="h-100">
        <LoadingSpan v-if="!loaded && !errorMessage" message="Loading admin extension" />
        <div v-else-if="errorMessage" class="alert alert-danger" role="alert">{{ errorMessage }}</div>
        <div v-else-if="!item" class="alert alert-warning" role="alert">
            No admin extension item "{{ props.itemId }}" found in extension "{{ props.extensionId }}".
        </div>
        <CenterFrame v-else :id="frameId" :src="item.url" />
    </div>
</template>
