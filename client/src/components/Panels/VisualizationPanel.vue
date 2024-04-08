<script setup lang="ts">
import { computed, onMounted, type Ref, ref } from "vue";

import { absPath } from "@/utils/redirect";
import { urlData } from "@/utils/url";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Plugin {
    description: string;
    name: string;
    html: string;
    logo?: string;
}

const plugins: Ref<Array<Plugin>> = ref([]);
const query = ref("");
const isLoading = ref(true);

const filteredPlugins = computed(() => {
    const queryLower = query.value.toLowerCase();
    return plugins.value.filter(
        (plugin) =>
            !query.value ||
            plugin.html.toLowerCase().includes(queryLower) ||
            (plugin.description && plugin.description.toLowerCase().includes(queryLower))
    );
});

onMounted(() => {
    getPlugins();
});

async function getPlugins() {
    plugins.value = await urlData({ url: "/api/plugins" });
    isLoading.value = false;
}
</script>

<template>
    <ActivityPanel title="Visualizations" go-to-all-title="Saved Visualizations" href="/visualizations/list">
        <h3>Create Visualization</h3>
        <DelayedInput :delay="100" placeholder="Search visualizations" @change="query = $event" />
        <div class="overflow-y mt-2">
            <LoadingSpan v-if="isLoading" message="Loading visualizations"/>
            <div v-else-if="filteredPlugins.length > 0">
                <div v-for="plugin in filteredPlugins" :key="plugin.name">
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
            <BAlert v-else v-localize variant="info" show> No matching visualization found. </BAlert>
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
