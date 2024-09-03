<script setup lang="ts">
import { BCard, BTab, BTabs } from "bootstrap-vue";

import { useFileSources } from "@/composables/fileSources";

import ToLink from "./ToLink.vue";
import ToRemoteFile from "./ToRemoteFile.vue";
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
                <BTabs pills card vertical class="history-export-tabs">
                    <BTab title="to a link" title-link-class="tab-export-to-link" active>
                        <b-card-text>
                            <ToLink :history-id="props.historyId" />
                        </b-card-text>
                    </BTab>
                    <BTab title="to a remote file" title-link-class="tab-export-to-file">
                        <b-card-text>
                            <ToRemoteFile :history-id="props.historyId" />
                        </b-card-text>
                    </BTab>
                </BTabs>
            </BCard>
        </span>
        <span v-else>
            <ToLink :history-id="props.historyId" />
        </span>
    </span>
</template>
