<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";

import { createWhooshQuery } from "@/components/Panels/utilities";
import { useToolStore } from "@/stores/toolStore";

import ToolsListTable from "@/components/ToolsList/ToolsListTable.vue";

const toolStore = useToolStore();
const { loading } = storeToRefs(toolStore);

const whooshQuery = computed(() => createWhooshQuery({ section: "Get Data" }));

const toolsInGetDataSection = computed(() => Object.values(toolStore.getToolsById(whooshQuery.value)));

onMounted(async () => {
    await toolStore.fetchTools(whooshQuery.value);
});
</script>

<template>
    <div class="data-source-tools-upload">
        <ToolsListTable :tools="toolsInGetDataSection" :loading="loading" :grid-view="false" />
    </div>
</template>
