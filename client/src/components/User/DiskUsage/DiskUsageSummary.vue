<script setup lang="ts">
import { faSyncAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";

import { type AsyncTaskResultSummary, GalaxyApi } from "@/api";
import { fetchCurrentUserQuotaUsages, type QuotaUsage } from "@/api/users";
import { useConfig } from "@/composables/config";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";
import { bytesToString } from "@/utils/utils";

import QuotaUsageSummary from "@/components/User/DiskUsage/Quota/QuotaUsageSummary.vue";

const { config, isConfigLoaded } = useConfig(true);
const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);
const { isRunning: isRecalculateTaskRunning, waitForTask } = useTaskMonitor();

const quotaUsages = ref<QuotaUsage[]>();
const errorMessage = ref<string>();
const isRecalculating = ref<boolean>(false);

const niceTotalDiskUsage = computed(() => {
    if (!currentUser.value || currentUser.value.isAnonymous) {
        return "Unknown";
    }
    return bytesToString(currentUser.value.total_disk_usage, true);
});

const isRefreshing = computed(() => {
    return isRecalculateTaskRunning.value || isRecalculating.value;
});

watch(
    () => isRefreshing.value,
    (newValue, oldValue) => {
        // Make sure we reload the user and the quota usages when the recalculation is done
        if (oldValue && !newValue) {
            const includeHistories = false;
            userStore.loadUser(includeHistories);
            loadQuotaUsages();
        }
    },
);

async function displayRecalculationForSeconds(seconds: number) {
    return new Promise<void>((resolve) => {
        isRecalculating.value = true;

        setTimeout(() => {
            isRecalculating.value = false;
            resolve();
        }, seconds * 1000);
    });
}

async function onRefresh() {
    const { response, data, error } = await GalaxyApi().PUT("/api/users/current/recalculate_disk_usage");

    if (error) {
        errorMessage.value = errorMessageAsString(error);
        return;
    }

    if (response.status == 200) {
        // Wait for the task to complete
        const asyncTaskResponse = data as AsyncTaskResultSummary;
        waitForTask(asyncTaskResponse.id);
    } else if (response.status == 204) {
        // We cannot track any task, so just display the
        // recalculation message for a reasonable amount of time
        await displayRecalculationForSeconds(30);
    }
}

async function loadQuotaUsages() {
    try {
        const currentUserQuotaUsages = await fetchCurrentUserQuotaUsages();
        quotaUsages.value = currentUserQuotaUsages;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    }
}

onMounted(async () => {
    await loadQuotaUsages();
});
</script>
<template>
    <div>
        <b-alert v-if="errorMessage" variant="danger" show>
            <h2 v-localize class="alert-heading h-sm">Failed to access disk usage details.</h2>
            {{ errorMessage }}
        </b-alert>
        <b-container v-if="currentUser">
            <b-row v-if="isConfigLoaded && config.enable_quotas" class="justify-content-md-center">
                <QuotaUsageSummary v-if="quotaUsages" :quota-usages="quotaUsages" />
            </b-row>
            <h2 v-else id="basic-disk-usage-summary" class="text-center my-3">
                You're using <b>{{ niceTotalDiskUsage }}</b> of disk space.
            </h2>
        </b-container>
        <b-container class="text-center mb-5 w-75">
            <b-alert v-if="isRefreshing" class="refreshing-alert" variant="info" show>
                <b-spinner small class="mr-2" />
                <span v-localize>Recalculating disk usage... this may take some time, please check back later.</span>
            </b-alert>
            <b-button
                v-else
                id="refresh-disk-usage"
                title="Recalculate disk usage"
                variant="primary"
                @click="onRefresh">
                <FontAwesomeIcon :icon="faSyncAlt" class="mr-1" />
                <span v-localize>Refresh</span>
            </b-button>
        </b-container>
    </div>
</template>
