<script setup lang="ts">
import { faArchive, faBurn, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { type AnyUser, type HistorySummary, isUserOverQuota, userOwnsHistory } from "@/api";
import { useQuotaSourceNames } from "@/composables/quotaSourceNames";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import localize from "@/utils/localization";

import GAlert from "@/components/BaseComponents/GAlert.vue";

interface Props {
    history: HistorySummary;
    currentUser: AnyUser;
}

const props = defineProps<Props>();

const ownsHistory = computed(() => userOwnsHistory(props.currentUser, props.history));
const showArchived = computed(() => props.history.archived && ownsHistory.value);

// The quota concerns the user, not the history: only warn about it on their own histories.
const isOverQuota = computed(() => ownsHistory.value && isUserOverQuota(props.currentUser));

// Jobs are paused per storage source, so name the other sources the user exceeded the quota of
const { otherSourcesOverQuota } = storeToRefs(useQuotaUsageStore());
const { otherSourcesOverQuotaNames } = useQuotaSourceNames();
const showOtherSourcesOverQuota = computed(() => ownsHistory.value && otherSourcesOverQuota.value.length > 0);
// The names follow a colon, so each sentence translates whole
const otherSourcesOverQuotaMessage = computed(
    () =>
        `${localize("You are over your disk quota on these storages:")} ${otherSourcesOverQuotaNames.value}. ` +
        localize("Jobs writing there are on hold until your usage there drops below the quota."),
);

const hasMessages = computed(
    () =>
        props.history.purged ||
        props.history.deleted ||
        showArchived.value ||
        isOverQuota.value ||
        showOtherSourcesOverQuota.value,
);
</script>

<template>
    <div v-if="hasMessages" class="mx-3 mt-2" data-description="history messages">
        <GAlert v-if="history.purged" variant="warning">
            <FontAwesomeIcon :icon="faBurn" fixed-width />
            {{ localize("History has been permanently deleted") }}
        </GAlert>
        <GAlert v-else-if="history.deleted" variant="warning">
            <FontAwesomeIcon :icon="faTrash" fixed-width />
            {{ localize("History has been deleted") }}
        </GAlert>

        <GAlert v-if="showArchived" variant="warning">
            <FontAwesomeIcon :icon="faArchive" fixed-width />
            {{ localize("History has been archived") }}
        </GAlert>

        <GAlert v-if="isOverQuota" variant="warning" data-description="over quota message">
            {{
                localize(
                    "You are over your disk quota. Tool execution is on hold until your disk usage drops below your allocated quota.",
                )
            }}
        </GAlert>

        <GAlert v-if="showOtherSourcesOverQuota" variant="warning" data-description="other sources over quota message">
            {{ otherSourcesOverQuotaMessage }}
        </GAlert>
    </div>
</template>
