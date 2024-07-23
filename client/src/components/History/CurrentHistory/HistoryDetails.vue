<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArchive, faBurn, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";

import type { HistorySummary } from "@/api";
import { useHistoryStore } from "@/stores/historyStore";

import type { DetailsLayoutSummarized } from "../Layout/types";

import TextSummary from "@/components/Common/TextSummary.vue";
import DetailsLayout from "@/components/History/Layout/DetailsLayout.vue";
import UtcDate from "@/components/UtcDate.vue";

library.add(faArchive, faBurn, faTrash);

interface Props {
    history: HistorySummary;
    writeable: boolean;
    summarized?: DetailsLayoutSummarized;
}

const props = withDefaults(defineProps<Props>(), {
    writeable: true,
    summarized: undefined,
});

const historyStore = useHistoryStore();

function onSave(newDetails: HistorySummary) {
    const id = props.history.id;
    historyStore.updateHistory({ ...newDetails, id });
}
</script>

<template>
    <DetailsLayout
        :name="history.name"
        :annotation="history.annotation || ''"
        :tags="history.tags"
        :writeable="writeable"
        :summarized="summarized"
        :update-time="history.update_time"
        @save="onSave">
        <template v-slot:name>
            <!-- eslint-disable-next-line vuejs-accessibility/heading-has-content -->
            <h3 v-if="!summarized" v-short="history.name || 'History'" data-description="name display" class="my-2" />
            <TextSummary
                v-else
                :description="history.name"
                data-description="name display"
                class="my-2"
                component="h3"
                one-line-summary
                no-expand />
        </template>
        <template v-if="summarized" v-slot:update-time>
            <BBadge v-b-tooltip pill>
                <span v-localize>last edited </span>
                <UtcDate v-if="history.update_time" :date="history.update_time" mode="elapsed" />
            </BBadge>
            <BBadge v-if="history.purged" pill class="alert-warning">
                <FontAwesomeIcon :icon="faBurn" />
                <span v-localize> Purged</span>
            </BBadge>
            <BBadge v-else-if="history.deleted" pill class="alert-danger">
                <FontAwesomeIcon :icon="faTrash" />
                <span v-localize> Deleted</span>
            </BBadge>
            <BBadge v-if="history.archived" pill class="alert-warning">
                <FontAwesomeIcon :icon="faArchive" />
                <span v-localize> Archived</span>
            </BBadge>
        </template>
    </DetailsLayout>
</template>
