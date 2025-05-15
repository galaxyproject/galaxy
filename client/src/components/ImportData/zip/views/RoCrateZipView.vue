<script setup lang="ts">
import { faUniversity, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { sanitize } from "dompurify";
import { onMounted, ref } from "vue";

import { type CardBadge } from "@/components/Common/GCard.types";
import type { ROCrateZipExplorer } from "@/composables/zipExplorer";
import { isGalaxyHistoryExport, isGalaxyZipExport } from "@/composables/zipExplorer";

import { extractROCrateSummary, type ROCrateSummary } from "./rocrate.utils";

import DOILink from "@/components/Common/DOILink.vue";
import GCard from "@/components/Common/GCard.vue";
import ExternalLink from "@/components/ExternalLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

const props = defineProps<{
    explorer: ROCrateZipExplorer;
}>();

const crateSummary = ref<ROCrateSummary>();
const badges = buildBadges();

function buildBadges(): CardBadge[] {
    const badges: CardBadge[] = [
        {
            id: "rocrate",
            label: "RO-Crate",
            title: "This archive contains an RO-Crate. A Research Object Crate (RO-Crate) is a structured package for sharing research data.",
            variant: "info",
            visible: true,
        },
    ];
    if (isGalaxyZipExport(props.explorer)) {
        if (isGalaxyHistoryExport(props.explorer)) {
            badges.push({
                id: "galaxy-history-export-badge",
                label: "Galaxy History",
                title: "This archive contains the exported datasets of a Galaxy History.",
                variant: "info",
                visible: true,
            });
        } else {
            badges.push({
                id: "galaxy-invocation-export-badge",
                label: "Galaxy Workflow Run",
                title: "This archive contains the exported results of a Galaxy workflow invocation or run.",
                variant: "info",
                visible: true,
            });
        }
    }
    return badges;
}

onMounted(async () => {
    crateSummary.value = await extractROCrateSummary(props.explorer.crate);
});
</script>

<template>
    <GCard
        v-if="crateSummary"
        id="rocrate-summary"
        class="mt-1"
        :badges="badges"
        :title="crateSummary.name"
        title-size="md">
        <template v-slot:titleBadges>
            <div>
                <strong>Publication Date:</strong>
                <UtcDate :date="crateSummary.publicationDate.toISOString()" mode="pretty" />
                (<UtcDate :date="crateSummary.publicationDate.toISOString()" mode="elapsed" />)
            </div>

            <div v-if="crateSummary.identifier">
                <strong>DOI:</strong>
                <DOILink :doi="crateSummary.identifier" />
            </div>
        </template>

        <template v-slot:description>
            <div v-html="sanitize(crateSummary.description)"></div>

            <div><strong>License:</strong> {{ crateSummary.license }}</div>

            <div v-if="crateSummary.creators.length > 0">
                <strong>Creators</strong>
                <div class="d-flex flex-wrap flex-gapx-1 flex-gapy-1 px-1">
                    <BBadge
                        v-for="creator in crateSummary.creators"
                        :key="creator.id"
                        variant="outline-secondary"
                        class="outline-badge">
                        <span v-if="creator.type === 'Person'">
                            <FontAwesomeIcon :icon="faUser" />
                        </span>
                        <span v-else-if="creator.type === 'Organization'">
                            <FontAwesomeIcon :icon="faUniversity" />
                        </span>
                        {{ creator.name }}
                    </BBadge>
                </div>
            </div>

            <div v-if="crateSummary.conformsTo.length > 0">
                <strong>Conforms To</strong>
                <div class="d-flex flex-wrap flex-gapx-1 flex-gapy-1 px-1">
                    <BBadge
                        v-for="conform in crateSummary.conformsTo"
                        :key="conform.id"
                        variant="outline-secondary"
                        class="outline-badge">
                        <ExternalLink :href="conform.id"> {{ conform.name }} {{ conform.version }} </ExternalLink>
                    </BBadge>
                </div>
            </div>
        </template>
    </GCard>
    <div v-else>
        <LoadingSpan message="Loading RO-Crate summary..." />
    </div>
</template>
