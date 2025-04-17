<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { fetchPlugins, type Plugin } from "@/api/plugins";

import ButtonPlain from "@/components/Common/ButtonPlain.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import VisualizationHeader from "@/components/Visualizations/VisualizationHeader.vue";

const router = useRouter();

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

async function selectVisualization(plugin: Plugin) {
    router.push(`/visualizations/create?visualization=${plugin.name}`);
}

async function getPlugins() {
    plugins.value = await fetchPlugins();
    isLoading.value = false;
}

onMounted(() => {
    getPlugins();
});
</script>

<template>
    <ActivityPanel title="Visualizations" go-to-all-title="Saved Visualizations" href="/visualizations/list">
        <template v-slot:header>
            <h3>Create Visualization</h3>
            <DelayedInput :delay="100" placeholder="Search visualizations" @change="query = $event" />
        </template>
        <div>
            <LoadingSpan v-if="isLoading" message="Loading visualizations" />
            <div v-else-if="filteredPlugins.length > 0">
                <div v-for="plugin in filteredPlugins" :key="plugin.name">
                    <ButtonPlain
                        class="plugin-item rounded p-2"
                        :data-plugin-name="plugin.name"
                        @click="selectVisualization(plugin)">
                        <VisualizationHeader :plugin="plugin" />
                    </ButtonPlain>
                </div>
            </div>
            <BAlert v-else v-localize variant="info" show> No matching visualization found. </BAlert>
        </div>
    </ActivityPanel>
</template>

<style lang="scss">
@import "theme/blue.scss";

.plugin-item:hover {
    background: $gray-200;
}
</style>
