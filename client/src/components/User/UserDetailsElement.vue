<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faAt, faHdd, faUser } from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { RouterLink } from "vue-router";

import { isRegisteredUser } from "@/api";
import { useUserStore } from "@/stores/userStore";

import GCard from "@/components/Common/GCard.vue";

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const userUsername = computed(() => (isRegisteredUser(currentUser.value) && currentUser.value?.username) || "");
const userEmail = computed(() => isRegisteredUser(currentUser.value) && currentUser.value?.email);
const userDiskUsagePercentage = computed(() => currentUser.value?.quota_percent || 0);
const userQuota = computed(() => !currentUser.value?.isAnonymous && currentUser.value?.quota);
const diskUsage = computed(() => currentUser.value?.nice_total_disk_usage);

const getStoragePercentageClass = (percentage: number) => {
    if (percentage >= 90) {
        return "text-danger";
    } else if (percentage >= 75) {
        return "text-warning";
    } else {
        return "text-primary";
    }
};
</script>

<template>
    <GCard content-class="user-details-element">
        <div class="user-details d-flex flex-gapx-1 flex-gapy-1 w-100 justify-content-between">
            <div class="d-flex align-items-center flex-gapx-1">
                <div class="d-flex align-items-center flex-gapx-1 mr-5">
                    <FontAwesomeIcon :icon="faUser" class="user-details-icon p-2" />
                    <span v-b-tooltip.hover.noninteractive title="Your username (public name)">
                        {{ userUsername }}
                    </span>
                </div>

                <div class="d-flex align-items-center flex-gapx-1">
                    <FontAwesomeIcon :icon="faAt" class="user-details-icon p-2" />
                    <span
                        id="user-preferences-current-email"
                        v-b-tooltip.hover.noninteractive
                        title="Your email address">
                        {{ userEmail }}
                    </span>
                </div>
            </div>

            <div class="flex flex-gapy-1">
                <div>
                    You are using
                    <b :class="getStoragePercentageClass(userDiskUsagePercentage)">
                        {{ diskUsage }} of {{ userQuota }} ({{ userDiskUsagePercentage }}%)
                    </b>
                    of your storage quota.
                </div>

                <div>
                    Visit
                    <RouterLink
                        v-b-tooltip.hover.noninteractive
                        to="/storage/dashboard"
                        title="View and manage your storage usage"
                        data-description="storage dashboard link">
                        <FontAwesomeIcon :icon="faHdd" />
                        Storage Dashboard
                    </RouterLink>
                    to manage your storage.
                </div>
            </div>
        </div>
    </GCard>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

.user-details-element {
    container: user-details-element;

    .user-details {
        align-items: center;

        @container (max-width: #{$breakpoint-md}) {
            flex-direction: column;
            align-items: flex-start;
        }

        .user-details-icon {
            color: $brand-primary;
            font-size: $h5-font-size;
            border: $border-default;
            border-color: $brand-primary;
            border-radius: $border-radius-extralarge;
        }
    }
}
</style>
