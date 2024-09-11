<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArchive, faBurn, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type AnyUser, type HistorySummary, userOwnsHistory } from "@/api";
import localize from "@/utils/localization";

library.add(faArchive, faBurn, faTrash);

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
        <BAlert v-if="history.purged" :show="history.purged" variant="warning">
            <FontAwesomeIcon :icon="faBurn" fixed-width />
            {{ localize("History has been permanently deleted") }}
        </BAlert>
        <BAlert v-else-if="history.deleted" :show="history.deleted" variant="warning">
            <FontAwesomeIcon :icon="faTrash" fixed-width />
            {{ localize("History has been deleted") }}
        </BAlert>

        <BAlert :show="history.archived && currentUserOwnsHistory" variant="warning">
            <FontAwesomeIcon :icon="faArchive" fixed-width />
            {{ localize("History has been archived") }}
        </BAlert>

        <BAlert :show="userOverQuota" variant="warning">
            {{
                localize(
                    "You are over your disk quota. Tool execution is on hold until your disk usage drops below your allocated quota."
                )
            }}
        </BAlert>
    </div>
</template>
