<script setup lang="ts">
import { faCaretDown, faCaretRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import { stripQuotes } from "@/utils/filtering";

import { type InvocationFilterMatches, NAME_MATCH_LIMIT } from "./configs/invocationFilters";

import GButton from "@/components/BaseComponents/GButton.vue";
import HistoryCardList from "@/components/History/HistoryCardList.vue";
import WorkflowCardList from "@/components/Workflow/List/WorkflowCardList.vue";

interface Props {
    matches?: InvocationFilterMatches;
}

defineProps<Props>();

const showWorkflows = ref(true);
const showHistories = ref(true);

function matchText(count: number, singular: string, plural: string, search: string) {
    const noun = count === 1 ? singular : plural;
    return `${count === 0 ? "No" : count} ${noun} ${count === 1 ? "matches" : "match"} "${stripQuotes(search)}"`;
}
</script>

<template>
    <div v-if="matches?.workflows || matches?.histories" class="invocation-filter-matches mb-2">
        <section v-if="matches.workflows" data-description="invocation filter workflow matches">
            <GButton
                transparent
                class="font-weight-bold p-0"
                :disabled="matches.workflows.items.length === 0"
                @click="showWorkflows = !showWorkflows">
                <FontAwesomeIcon
                    v-if="matches.workflows.items.length > 0"
                    :icon="showWorkflows ? faCaretDown : faCaretRight"
                    fixed-width />
                {{ matchText(matches.workflows.items.length, "workflow", "workflows", matches.workflows.search) }}
            </GButton>
            <p v-if="matches.workflows.truncated" class="text-muted small mb-1">
                More workflows match. Only the first {{ NAME_MATCH_LIMIT }} of each kind (yours, deleted, hidden) are
                used, so use a more specific name.
            </p>
            <WorkflowCardList
                v-if="showWorkflows && matches.workflows.items.length > 0"
                class="invocation-filter-matches-list"
                :workflows="matches.workflows.items"
                :selectable="false"
                :filterable="false" />
        </section>
        <section v-if="matches.histories" data-description="invocation filter history matches">
            <GButton
                transparent
                class="font-weight-bold p-0"
                :disabled="matches.histories.items.length === 0"
                @click="showHistories = !showHistories">
                <FontAwesomeIcon
                    v-if="matches.histories.items.length > 0"
                    :icon="showHistories ? faCaretDown : faCaretRight"
                    fixed-width />
                {{ matchText(matches.histories.items.length, "history", "histories", matches.histories.search) }}
            </GButton>
            <p v-if="matches.histories.truncated" class="text-muted small mb-1">
                More histories match. Only the first {{ NAME_MATCH_LIMIT }} of each kind (active, deleted, purged) are
                used, so use a more specific name.
            </p>
            <HistoryCardList
                v-if="showHistories && matches.histories.items.length > 0"
                class="invocation-filter-matches-list"
                :histories="matches.histories.items" />
        </section>
    </div>
</template>

<style scoped lang="scss">
.invocation-filter-matches-list {
    max-height: 18rem;
}
</style>
