<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArchive, faBurn, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";

import { type HistorySummary, userOwnsHistory } from "@/api";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import UtcDate from "../UtcDate.vue";

library.add(faArchive, faBurn, faTrash);

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const props = defineProps<{
    history: HistorySummary;
    includeCount?: boolean;
    detailedTime?: boolean;
}>();
</script>

<template>
    <div class="d-flex align-items-center flex-gapx-1">
        <BBadge v-if="props.includeCount" pill :title="localize('Amount of items in history')">
            {{ history.count }} {{ localize("items") }}
        </BBadge>
        <BBadge v-if="history.update_time" pill :title="localize('Last edited')">
            <span v-if="props.detailedTime" v-localize>last edited </span>
            <UtcDate :date="history.update_time" mode="elapsed" />
        </BBadge>
        <BBadge v-if="props.history.purged" pill class="alert-warning" title="Permanently deleted">
            <FontAwesomeIcon :icon="faBurn" fixed-width />
        </BBadge>
        <BBadge v-else-if="history.deleted" pill class="alert-danger" title="Deleted">
            <FontAwesomeIcon :icon="faTrash" fixed-width />
        </BBadge>
        <BBadge v-if="history.archived && userOwnsHistory(currentUser, props.history)" pill title="Archived">
            <FontAwesomeIcon :icon="faArchive" fixed-width />
        </BBadge>
    </div>
</template>
