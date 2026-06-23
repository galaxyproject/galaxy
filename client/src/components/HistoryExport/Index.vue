<script setup lang="ts">
import { BCard } from "bootstrap-vue";

import { useFileSources } from "@/composables/fileSources";

import ToLink from "./ToLink.vue";
import ToRemoteFile from "./ToRemoteFile.vue";
import GTab from "@/components/BaseComponents/GTab.vue";
import GTabs from "@/components/BaseComponents/GTabs.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { isLoading: initializingFileSources, hasWritable: hasWritableFileSources } = useFileSources();

interface ExportHistoryProps {
    historyId: string;
}

const props = defineProps<ExportHistoryProps>();
</script>
<template>
    <span class="history-export-component">
        <h1 class="h-lg">Export history archive</h1>
        <span v-if="initializingFileSources">
            <LoadingSpan message="Loading file sources configuration from Galaxy server." />
        </span>
        <span v-else-if="hasWritableFileSources">
            <BCard no-body>
                <GTabs pills card vertical class="history-export-tabs">
                    <GTab title="to a link" title-link-class="tab-export-to-link" active>
                        <ToLink :history-id="props.historyId" />
                    </GTab>
                    <GTab title="to a repository" title-link-class="tab-export-to-file">
                        <ToRemoteFile :history-id="props.historyId" />
                    </GTab>
                </GTabs>
            </BCard>
        </span>
        <span v-else>
            <ToLink :history-id="props.historyId" />
        </span>
    </span>
</template>
