<script setup lang="ts">
import { useHistoryStore } from "@/stores/historyStore";

import HistoriesStorageOverview from "./HistoriesStorageOverview.vue";
import HistoryCarbonEmissions from "./HistoryCarbonEmissions.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{ historyId: string }>();

const { getHistoryNameById } = useHistoryStore();
</script>

<template>
    <div>
        <header class="mt-4">
            <Heading h1 separator bold> History Statistics </Heading>

            <p>
                Here is a summary of the statistics of the history
                <strong>{{ getHistoryNameById(props.historyId) }}</strong
                >.
            </p>

            <p>
                As you continue to work on your current history, we collect statistics such as your history's storage
                metrics or the aggregated energy usage of all jobs in the history.
            </p>
        </header>

        <section class="mt-3">
            <Heading h2 bold separator> Carbon Emissions </Heading>
            <HistoryCarbonEmissions :history-id="props.historyId" />
        </section>

        <section class="mt-3">
            <Heading h2 bold separator> Storage Overview </Heading>
            <HistoriesStorageOverview />
        </section>
    </div>
</template>
