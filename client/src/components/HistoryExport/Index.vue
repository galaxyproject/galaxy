<script setup lang="ts">
import { GCard, GCardText, GTab, GTabs } from "@/component-library";
import { useFileSources } from "@/composables/fileSources";

import ToLink from "./ToLink.vue";
import ToRemoteFile from "./ToRemoteFile.vue";

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
            <loading-span message="Loading file sources configuration from Galaxy server." />
        </span>
        <span v-else-if="hasWritableFileSources">
            <GCard no-body>
                <GTabs pills card vertical>
                    <GTab title="to a link" title-link-class="tab-export-to-link" active>
                        <GCardText>
                            <ToLink :history-id="props.historyId" />
                        </GCardText>
                    </GTab>
                    <GTab title="to a remote file" title-link-class="tab-export-to-file">
                        <GCardText>
                            <ToRemoteFile :history-id="props.historyId" />
                        </GCardText>
                    </GTab>
                </GTabs>
            </GCard>
        </span>
        <span v-else>
            <ToLink :history-id="props.historyId" />
        </span>
    </span>
</template>
