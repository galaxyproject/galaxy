<script setup lang="ts">
import type { ExportRecord } from "@/components/Common/models/exportRecordModel";

import IncludedBadge from "./IncludedBadge.vue";
import GCard from "@/component-library/GCard.vue";
import GCardText from "@/component-library/GCardText.vue";

const props = defineProps<{
    exportRecord: ExportRecord;
}>();
</script>

<template>
    <GCard id="export-record-ready">
        <GCardText>
            <b>Exported {{ props.exportRecord.elapsedTime }}</b> on {{ props.exportRecord.date }}
        </GCardText>
        <GCardText v-if="props.exportRecord.exportParams">
            <b>Contains datasets:</b>
            <IncludedBadge item-name="active" :included="props.exportRecord.exportParams.includeFiles" />
            <IncludedBadge item-name="hidden" :included="props.exportRecord.exportParams.includeHidden" />
            <IncludedBadge item-name="deleted" :included="props.exportRecord.exportParams.includeDeleted" />
        </GCardText>
        <GCardText> <b>Stored in:</b> {{ props.exportRecord.importUri }} </GCardText>
    </GCard>
</template>
