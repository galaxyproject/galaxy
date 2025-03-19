<script setup lang="ts">
import type { ROCrateImmutableView } from "ro-crate-zip-explorer";
import { onMounted, ref } from "vue";

import { extractROCrateSummary, type ROCrateSummary } from "./rocrate.utils";

import ExternalLink from "@/components/ExternalLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    crate: ROCrateImmutableView;
}

const props = defineProps<Props>();

const crateSummary = ref<ROCrateSummary>();

onMounted(async () => {
    crateSummary.value = await extractROCrateSummary(props.crate);
});
</script>

<template>
    <div v-if="crateSummary" class="rocrate-explorer">
        <h2>RO-Crate Summary</h2>

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
