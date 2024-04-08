<script setup lang="ts">
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import PluginList from "@/components/Visualizations/PluginList.vue";
</script>

<template>
    <ActivityPanel title="Visualizations" go-to-all-title="Saved Visualizations" href="/visualizations/list">
        <h3>Create Visualization</h3>
        <PluginList />
    </ActivityPanel>
</template>
