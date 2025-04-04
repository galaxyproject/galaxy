<script setup lang="ts">
import { onMounted, ref } from "vue";

import type { ROCrateZipExplorer } from "@/composables/zipExplorer";

import { extractROCrateSummary, type ROCrateSummary } from "./rocrate.utils";

import Heading from "@/components/Common/Heading.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

const props = defineProps<{
    explorer: ROCrateZipExplorer;
}>();

const crateSummary = ref<ROCrateSummary>();

onMounted(async () => {
    crateSummary.value = await extractROCrateSummary(props.explorer.crate);
});
</script>

<template>
    <div v-if="crateSummary" class="rocrate-explorer">
        <Heading size="lg">RO-Crate Summary</Heading>

        <div>
            <strong>Publication Date:</strong>
            <UtcDate :date="crateSummary.publicationDate.toISOString()" mode="pretty" />
            (<UtcDate :date="crateSummary.publicationDate.toISOString()" mode="elapsed" />)
        </div>

        <strong>License:</strong> {{ crateSummary.license }}

        <div v-if="crateSummary.creators.length > 0">
            <strong>Creators</strong>
            <ul>
                <li v-for="creator in crateSummary.creators" :key="creator.id">
                    {{ creator.name }}
                </li>
            </ul>
        </div>

        <div v-if="crateSummary.conformsTo.length > 0">
            <strong>Conforms To</strong>
            <ul>
                <li v-for="conform in crateSummary.conformsTo" :key="conform.id">
                    <ExternalLink :href="conform.id"> {{ conform.name }} {{ conform.version }} </ExternalLink>
                </li>
            </ul>
        </div>
    </div>
    <div v-else>
        <LoadingSpan message="Loading RO-Crate summary..." />
    </div>
</template>
