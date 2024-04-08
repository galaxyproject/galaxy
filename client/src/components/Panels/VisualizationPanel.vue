<script setup lang="ts">
import { onMounted, ref } from "vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import PluginList from "@/components/Visualizations/PluginList.vue";
import { urlData } from "@/utils/url";

const plugins = ref([]);

onMounted(() => {
    getPlugins();
});

async function getPlugins() {
    plugins.value = await urlData({ url: "/api/plugins" });
}

</script>

<template>
    <ActivityPanel title="Visualizations" go-to-all-title="Saved Visualizations" href="/visualizations/list">
        <h3>Create Visualization</h3>
        <div class="card-container">
            stuff
        </div>
    </ActivityPanel>
</template>
