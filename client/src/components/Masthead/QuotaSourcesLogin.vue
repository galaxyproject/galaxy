<script setup lang="ts">
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";

defineProps<{
    /** Whether the user exceeded the quota of the default storage */
    isOverDefaultQuota: boolean;
}>();
</script>

<template>
    <div>
        <div v-if="isOverDefaultQuota" class="text-danger small mb-2" data-description="anonymous over quota">
            <FontAwesomeIcon :icon="faExclamationTriangle" />
            {{ localize("Over quota on the default storage: jobs writing there are on hold") }}
        </div>
        <p class="mb-2" data-description="log in for storage usage">
            {{ localize("Log in to see your usage and quota on each storage.") }}
        </p>
        <GButton class="w-100" color="blue" size="small" to="/login/start" data-description="log in button">
            {{ localize("Log in") }}
        </GButton>
    </div>
</template>
