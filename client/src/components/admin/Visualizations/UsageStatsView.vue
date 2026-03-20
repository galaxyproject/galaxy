<template>
    <div>
        <div class="d-flex justify-content-between align-items-center mb-3">
            <Heading h3 size="md">Usage Statistics</Heading>
            <b-button variant="outline-secondary" :disabled="loading" @click="emit('refresh')">
                <FontAwesomeIcon :icon="faSync" :spin="loading" class="mr-1" />
                Refresh
            </b-button>
        </div>

        <div v-if="loading" class="text-center py-4">
            <b-spinner label="Loading..." />
            <p class="mt-2">Loading usage statistics...</p>
        </div>

        <div v-else-if="stats.message" class="text-center py-4">
            <BAlert variant="info" show>
                <FontAwesomeIcon :icon="faInfoCircle" class="mr-2" />
                {{ stats.message }}
            </BAlert>
            <p class="text-muted">Usage tracking will be implemented in a future version.</p>
        </div>

        <div v-else-if="hasStats">
            <div class="row mb-4">
                <div class="col-md-4">
                    <b-card class="text-center">
                        <h4 class="text-primary">{{ totalUsage }}</h4>
                        <p class="text-muted mb-0">Total Visualizations Used</p>
                    </b-card>
                </div>
                <div class="col-md-4">
                    <b-card class="text-center">
                        <h4 class="text-success">{{ activeVisualizations }}</h4>
                        <p class="text-muted mb-0">Active Visualizations</p>
                    </b-card>
                </div>
                <div class="col-md-4">
                    <b-card class="text-center">
                        <h4 class="text-info">{{ stats.days }}</h4>
                        <p class="text-muted mb-0">Days Analyzed</p>
                    </b-card>
                </div>
            </div>

            <b-card>
                <template v-slot:header>
                    <h5 class="mb-0">Usage by Visualization</h5>
                </template>

                <div v-if="Object.keys(stats.stats).length === 0" class="text-center text-muted py-3">
                    No usage data available for the selected period.
                </div>
                <div v-else>
                    <div
                        v-for="(count, vizId) in sortedStats"
                        :key="vizId"
                        class="d-flex justify-content-between align-items-center py-2 border-bottom">
                        <div>
                            <strong>{{ vizId }}</strong>
                        </div>
                        <div class="d-flex align-items-center">
                            <b-progress class="mr-3" style="width: 100px; height: 20px">
                                <b-progress-bar :value="getPercentage(count as number)" :max="100" />
                            </b-progress>
                            <b-badge variant="primary">{{ count }}</b-badge>
                        </div>
                    </div>
                </div>
            </b-card>
        </div>

        <div v-else class="text-center py-4">
            <p class="text-muted">No usage statistics available.</p>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faInfoCircle, faSync } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import type { UsageStats } from "./services";

import Heading from "@/components/Common/Heading.vue";

interface Props {
    loading?: boolean;
    stats?: UsageStats;
}

const props = withDefaults(defineProps<Props>(), {
    loading: false,
    stats: () => ({ days: 30, stats: {} }) as UsageStats,
});

const emit = defineEmits<{
    (e: "refresh"): void;
}>();

const hasStats = computed(() => {
    return props.stats && typeof props.stats.stats === "object" && Object.keys(props.stats.stats).length > 0;
});

const totalUsage = computed(() => {
    if (!hasStats.value) {
        return 0;
    }
    return Object.values(props.stats.stats).reduce((sum, count) => sum + count, 0);
});

const activeVisualizations = computed(() => {
    if (!hasStats.value) {
        return 0;
    }
    return Object.keys(props.stats.stats).length;
});

const sortedStats = computed(() => {
    if (!hasStats.value) {
        return {};
    }
    const entries = Object.entries(props.stats.stats);
    entries.sort((a, b) => (b[1] as number) - (a[1] as number));
    return Object.fromEntries(entries);
});

const maxUsage = computed(() => {
    if (!hasStats.value) {
        return 0;
    }
    const values = Object.values(props.stats.stats) as number[];
    return values.length > 0 ? Math.max(...values) : 0;
});

function getPercentage(count: number): number {
    if (maxUsage.value === 0) {
        return 0;
    }
    return (count / maxUsage.value) * 100;
}
</script>

<style scoped>
.border-bottom:last-child {
    border-bottom: none !important;
}
</style>
