<script setup lang="ts">
import { type ROCrateSummary } from "./rocrate.utils";

import ExternalLink from "@/components/ExternalLink.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    crateSummary: ROCrateSummary;
}

const props = defineProps<Props>();
</script>

<template>
    <div class="rocrate-explorer">
        <h2>RO-Crate Summary</h2>

        <div>
            <strong>Publication Date:</strong>
            <UtcDate :date="props.crateSummary.publicationDate.toISOString()" mode="pretty" />
            (<UtcDate :date="props.crateSummary.publicationDate.toISOString()" mode="elapsed" />)
        </div>

        <strong>License:</strong> {{ props.crateSummary.license }}

        <div v-if="props.crateSummary.creators.length > 0">
            <strong>Creators</strong>
            <ul>
                <li v-for="creator in props.crateSummary.creators" :key="creator.id">
                    {{ creator.name }}
                </li>
            </ul>
        </div>

        <div v-if="props.crateSummary.conformsTo.length > 0">
            <strong>Conforms To</strong>
            <ul>
                <li v-for="conform in props.crateSummary.conformsTo" :key="conform.id">
                    <ExternalLink :href="conform.id"> {{ conform.name }} {{ conform.version }} </ExternalLink>
                </li>
            </ul>
        </div>
    </div>
</template>
