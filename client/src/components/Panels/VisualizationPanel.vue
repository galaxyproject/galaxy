<script setup lang="ts">
import { onMounted, type Ref, ref } from "vue";

import { absPath } from "@/utils/redirect";
import { urlData } from "@/utils/url";

import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

interface Plugin {
    description: string;
    name: string;
    html: string;
    logo?: string;
}

const plugins: Ref<Array<Plugin>> = ref([]);

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
        <div class="overflow-y">
            <div v-for="plugin in plugins" :key="plugin.name">
                <button :data-plugin-name="plugin.name">
                    <div class="d-flex">
                        <div class="plugin-thumbnail mr-3">
                            <img v-if="plugin.logo" alt="visualization" :src="absPath(plugin.logo)" />
                            <div v-else class="fa fa-eye" />
                        </div>
                        <div class="text-break">
                            <div class="plugin-list-title font-weight-bold">{{ plugin.html }}</div>
                            <div class="plugin-list-text">{{ plugin.description }}</div>
                        </div>
                    </div>
                </button>
            </div>
        </div>
    </ActivityPanel>
</template>

<style>
.plugin-thumbnail {
    img {
        width: 2rem;
    }
    div {
        font-size: 1.5rem;
        padding: 0.2rem;
    }
}
</style>
