<template>
    <div>
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h3>Usage Statistics</h3>
            <b-button variant="outline-secondary" :disabled="loading" @click="$emit('refresh')">
                <i class="fa fa-sync mr-1" :class="{ 'fa-spin': loading }"></i>
                Refresh
            </b-button>
        </div>

        <div v-if="loading" class="text-center py-4">
            <b-spinner label="Loading..."></b-spinner>
            <p class="mt-2">Loading usage statistics...</p>
        </div>

        <div v-else-if="stats.message" class="text-center py-4">
            <div class="alert alert-info">
                <i class="fa fa-info-circle mr-2"></i>
                {{ stats.message }}
            </div>
            <p class="text-muted">Usage tracking will be implemented in a future version.</p>
        </div>

        <div v-else-if="hasStats">
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body text-center">
                            <h4 class="text-primary">{{ totalUsage }}</h4>
                            <p class="text-muted mb-0">Total Visualizations Used</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body text-center">
                            <h4 class="text-success">{{ activeVisualizations }}</h4>
                            <p class="text-muted mb-0">Active Visualizations</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body text-center">
                            <h4 class="text-info">{{ stats.days }}</h4>
                            <p class="text-muted mb-0">Days Analyzed</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Usage by Visualization</h5>
                </div>
                <div class="card-body">
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
                                <div class="progress mr-3" style="width: 100px; height: 20px">
                                    <div
                                        class="progress-bar"
                                        role="progressbar"
                                        :style="{ width: getPercentage(count) + '%' }"
                                        :aria-valuenow="count"
                                        :aria-valuemin="0"
                                        :aria-valuemax="maxUsage"></div>
                                </div>
                                <span class="badge badge-primary">{{ count }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div v-else class="text-center py-4">
            <p class="text-muted">No usage statistics available.</p>
        </div>
    </div>
</template>

<script>
export default {
    name: "UsageStatsView",

    props: {
        loading: {
            type: Boolean,
            default: false,
        },
        stats: {
            type: Object,
            default: () => ({ days: 30, stats: {} }),
        },
    },

    computed: {
        hasStats() {
            return this.stats && typeof this.stats.stats === "object";
        },

        totalUsage() {
            if (!this.hasStats) {
                return 0;
            }
            return Object.values(this.stats.stats).reduce((sum, count) => sum + count, 0);
        },

        activeVisualizations() {
            if (!this.hasStats) {
                return 0;
            }
            return Object.keys(this.stats.stats).length;
        },

        sortedStats() {
            if (!this.hasStats) {
                return {};
            }

            const entries = Object.entries(this.stats.stats);
            entries.sort((a, b) => b[1] - a[1]); // Sort by usage count descending

            return Object.fromEntries(entries);
        },

        maxUsage() {
            if (!this.hasStats) {
                return 0;
            }
            const values = Object.values(this.stats.stats);
            return values.length > 0 ? Math.max(...values) : 0;
        },
    },

    methods: {
        getPercentage(count) {
            if (this.maxUsage === 0) {
                return 0;
            }
            return (count / this.maxUsage) * 100;
        },
    },
};
</script>

<style scoped>
.card {
    border: 1px solid #dee2e6;
    border-radius: 0.375rem;
}

.progress {
    background-color: #e9ecef;
}

.progress-bar {
    background-color: #007bff;
}

.border-bottom:last-child {
    border-bottom: none !important;
}
</style>
