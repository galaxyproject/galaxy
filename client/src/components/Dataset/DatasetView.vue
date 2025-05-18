<script setup lang="ts">
import { BNav, BNavItem } from "bootstrap-vue";
import { computed } from "vue";

import { useDatasetStore } from "@/stores/datasetStore";

import Heading from "@/components/Common/Heading.vue";

const datasetStore = useDatasetStore();

interface Props {
    username?: string;
    datasetId: string;
    tab?: "details" | "edit" | "view" | "visualize";
}

const props = withDefaults(defineProps<Props>(), {
    tab: "view",
    username: undefined,
});

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const isLoading = computed(() => datasetStore.isLoadingDataset(props.datasetId));
</script>

<template>
    <LoadingSpan v-if="isLoading"></LoadingSpan>
    <div v-else class="d-flex flex-column">
        <div class="d-flex">
            <Heading h1 separator inline size="lg" class="flex-grow-1 mb-2">
                {{ dataset?.hid }}: <span class="font-weight-bold">{{ dataset?.name }}</span>
            </Heading>
        </div>
        <BNav pills justified class="mb-2">
            <BNavItem :active="tab === 'view'" :to="`/datasets/${datasetId}/view`"> Preview </BNavItem>
            <BNavItem :active="tab === 'visualize'" :to="`/datasets/${datasetId}/visualize`"> Visualize </BNavItem>
            <BNavItem :active="tab === 'details'" :to="`/datasets/${datasetId}/details`"> Details </BNavItem>
            <BNavItem :active="tab === 'edit'" :to="`/datasets/${datasetId}/edit`"> Edit </BNavItem>
        </BNav>
        <div v-if="tab === 'view'">View</div>
        <div v-else-if="tab === 'visualize'">Visualize</div>
        <div v-else-if="tab === 'details'">Details</div>
        <div v-else>Edit</div>
    </div>
</template>
