<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";

import { useAdminExtensionsStore } from "@/stores/adminExtensionsStore";

import FormGeneric from "@/components/Form/FormGeneric.vue";
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
const elementId = computed(() => `admin-extension-${props.extensionId}-${props.itemId}`);
const formUrl = computed(() => `/api/admin/extensions/${props.extensionId}/items/${props.itemId}/form`);
</script>

<template>
    <div class="h-100">
        <LoadingSpan v-if="!loaded && !errorMessage" message="Loading admin extension" />
        <div v-else-if="errorMessage" class="alert alert-danger" role="alert">{{ errorMessage }}</div>
        <div v-else-if="!item" class="alert alert-warning" role="alert">
            No admin extension item "{{ props.itemId }}" found in extension "{{ props.extensionId }}".
        </div>
        <FormGeneric v-else-if="item.type === 'form'" :id="elementId" :url="formUrl" submit-title="Save" />
        <CenterFrame v-else :id="elementId" :src="item.url" />
    </div>
</template>
