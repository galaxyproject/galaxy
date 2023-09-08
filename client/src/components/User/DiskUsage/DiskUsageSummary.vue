<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useConfig } from "@/composables/config";
import { fetcher } from "@/schema";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";
import { bytesToString } from "@/utils/utils";

import { QuotaUsage } from "./Quota/model";

import QuotaUsageSummary from "@/components/User/DiskUsage/Quota/QuotaUsageSummary.vue";

const { config, isConfigLoaded } = useConfig(true);
const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const errorMessage = ref<string>();
const isRecalculating = ref<boolean>(false);
const dismissCountDown = ref<number>(0);

const niceTotalDiskUsage = computed(() => {
    if (!currentUser.value || currentUser.value.isAnonymous) {
        return "Unknown";
    }
    return bytesToString(currentUser.value.total_disk_usage, true);
});

const quotaUsages = computed(() => {
    if (!currentUser.value || currentUser.value.isAnonymous) {
        return [];
    }
    return [new QuotaUsage(currentUser.value)];
});

async function displayRecalculationForSeconds(seconds: number) {
    return new Promise<void>((resolve) => {
        isRecalculating.value = true;
        dismissCountDown.value = seconds;

        setTimeout(() => {
            isRecalculating.value = false;
            resolve();
        }, seconds * 1000);
    });
}

const recalculateDiskUsage = fetcher.path("/api/users/current/recalculate_disk_usage").method("put").create();

async function onRefresh() {
    try {
        await recalculateDiskUsage({});
        await displayRecalculationForSeconds(30);
        userStore.loadUser();
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    }
}

function onCountDownChanged(count: number) {
    dismissCountDown.value = count;
}
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
            <button
                title="Recalculate disk usage"
                :disabled="isRecalculating"
                variant="outline-secondary"
                size="sm"
                pill
                @click="onRefresh">
                <b-spinner v-if="isRecalculating" small />
                <span v-else>Refresh</span>
            </button>
            <b-alert
                v-if="isRecalculating"
                v-localize
                class="mt-2"
                variant="info"
                dismissible
                fade
                :show="dismissCountDown"
                @dismiss-count-down="onCountDownChanged">
                Recalculating disk usage... this may take some time, please check back later.
            </b-alert>
        </b-container>
    </div>
</template>
