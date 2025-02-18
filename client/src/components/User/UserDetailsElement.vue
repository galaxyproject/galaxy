<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faAt, faCloud, faHdd, faUser } from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { isRegisteredUser } from "@/api";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

const { config } = useConfig(true);

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const userUsername = computed(() => (isRegisteredUser(currentUser.value) && currentUser.value?.username) || "");
const userEmail = computed(() => isRegisteredUser(currentUser.value) && currentUser.value?.email);
const userDiskUsagePercentage = computed(() => currentUser.value?.quota_percent);
const userQuota = computed(() => !currentUser.value?.isAnonymous && currentUser.value?.quota);
const diskUsage = computed(() => currentUser.value?.nice_total_disk_usage);
</script>

<template>
    <div class="user-details-element">
        <div class="user-details-element-icon">
            <FontAwesomeIcon :icon="faUser" />
        </div>

        <div class="user-details-element-content">
            <div class="user-details-item">
                <FontAwesomeIcon :icon="faUser" />
                <span>{{ userUsername }}</span>
            </div>
            <div class="user-details-item">
                <FontAwesomeIcon :icon="faAt" />
                <span>{{ userEmail }}</span>
            </div>
            <div class="user-details-item">
                <FontAwesomeIcon :icon="faHdd" />
                <span>{{ diskUsage }}</span>
            </div>
            <div v-if="config?.enable_quotas" class="user-details-item">
                <FontAwesomeIcon :icon="faCloud" />
                <span>{{ userQuota }}</span>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.user-details-element {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    border: 1px solid $brand-secondary;
    border-radius: 0.75rem;
    padding: 0.75rem;
    width: 100%;
    margin-bottom: 1rem;

    .user-details-element-icon {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 2rem;
        border: 1px solid $brand-secondary;
        border-radius: 50%;
        padding: 0.5rem;
        color: $brand-secondary;
        width: 3rem;
        height: 3rem;
    }

    .user-details-element-content {
        display: flex;
        gap: 0.5rem;
    }
}
</style>
