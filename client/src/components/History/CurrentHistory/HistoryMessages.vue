<script setup lang="ts">
import { faArchive, faBurn, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import { type AnyUser, type HistorySummary, userOwnsHistory } from "@/api";
import localize from "@/utils/localization";

import GAlert from "@/components/BaseComponents/GAlert.vue";

interface Props {
    history: HistorySummary;
    currentUser: AnyUser;
}

const props = defineProps<Props>();

const userOverQuota = ref(false);

const hasMessages = computed(() => {
    return userOverQuota.value || props.history.deleted || props.history.archived;
});

const currentUserOwnsHistory = computed(() => {
    return userOwnsHistory(props.currentUser, props.history);
});
</script>

<template>
    <div v-if="hasMessages" class="mx-3 mt-2" data-description="history messages">
        <GAlert v-if="history.purged" :show="history.purged" variant="warning">
            <FontAwesomeIcon :icon="faBurn" fixed-width />
            {{ localize("History has been permanently deleted") }}
        </GAlert>
        <GAlert v-else-if="history.deleted" :show="history.deleted" variant="warning">
            <FontAwesomeIcon :icon="faTrash" fixed-width />
            {{ localize("History has been deleted") }}
        </GAlert>

        <GAlert :show="history.archived && currentUserOwnsHistory" variant="warning">
            <FontAwesomeIcon :icon="faArchive" fixed-width />
            {{ localize("History has been archived") }}
        </GAlert>

        <GAlert :show="userOverQuota" variant="warning">
            {{
                localize(
                    "You are over your disk quota. Tool execution is on hold until your disk usage drops below your allocated quota.",
                )
            }}
        </GAlert>
    </div>
</template>
