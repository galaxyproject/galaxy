<script setup lang="ts">
import { faEye } from "@fortawesome/free-solid-svg-icons";
import { BAlert } from "bootstrap-vue";
import { computed, onMounted, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { absPath } from "@/utils/redirect";
import { urlData } from "@/utils/url";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

interface Plugin {
    description: string;
    href: string;
    html: string;
    logo?: string;
    name: string;
    target?: string;
}

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
    console.log(plugin);
}

async function getPlugins() {
    plugins.value = await urlData({ url: "/api/plugins" });
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
                    <button class="plugin-item" :data-plugin-name="plugin.name" @click="selectVisualization(plugin)">
                        <div class="d-flex">
                            <div class="plugin-thumbnail mr-2">
                                <img v-if="plugin.logo" alt="visualization" :src="absPath(plugin.logo)" />
                                <icon v-else :icon="faEye" class="plugin-icon" />
                            </div>
                            <div class="text-break">
                                <div class="plugin-list-title font-weight-bold">{{ plugin.html }}</div>
                                <div class="plugin-list-text text-muted">{{ plugin.description }}</div>
                            </div>
                        </div>
                    </button>
                </div>
            </div>
            <BAlert v-else v-localize variant="info" show> No matching visualization found. </BAlert>
        </div>
    </ActivityPanel>
</template>

<style lang="scss">
@import "theme/blue.scss";

.plugin-item {
    background: none;
    border: none;
    text-align: left;
    transition: none;
    width: 100%;
}

.plugin-item:hover {
    background: $gray-200;
}

.plugin-thumbnail {
    img {
        width: 2rem;
    }
    .plugin-icon {
        font-size: 1.3rem;
        padding: 0.3rem;
    }
}
</style>
