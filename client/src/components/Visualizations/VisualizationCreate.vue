<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { fetchPlugin } from "@/api/plugins";
import { absPath } from "@/utils/redirect";
import SelectionField from "@/components/SelectionField/SelectionField.vue";

const props = defineProps<{
    visualization: string;
}>();

const errorMessage = ref("");
const isLoading = ref(false);
const plugin = ref();

async function getPlugin() {
    plugin.value = await fetchPlugin(props.visualization);
    isLoading.value = false;
}

onMounted(() => {
    getPlugin();
});
</script>

<template>
    <div v-if="errorMessage">
        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    </div>
    <div v-else>
        <LoadingSpan v-if="isLoading" message="Loading visualization" />
        <div v-else class="d-flex">
            <div class="plugin-thumbnail mr-2">
                <img v-if="plugin.logo" alt="visualization" :src="absPath(plugin.logo)" />
                <icon v-else icon="faEye" class="plugin-icon" />
            </div>
            <div class="text-break">
                <div class="plugin-list-title font-weight-bold">{{ plugin.html }}</div>
                <div class="plugin-list-text text-muted">{{ plugin.description }}</div>
            </div>
            <SelectionField object-title="Dataset" object-type="history_dataset_id" />
        </div>
    </div>
</template>
