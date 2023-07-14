<script setup lang="ts">
import { BCard, BCardText } from "bootstrap-vue";

import type { ExportRecord } from "@/components/Common/models/exportRecordModel";

import IncludedBadge from "./IncludedBadge.vue";

const props = defineProps<{
    exportRecord: ExportRecord;
}>();
</script>

<template>
    <BCard id="export-record-ready">
        <BCardText>
            <b>Exported {{ props.exportRecord.elapsedTime }}</b> on {{ props.exportRecord.date }}
        </BCardText>
        <BCardText v-if="props.exportRecord.exportParams">
            <b>Contains datasets:</b>
            <IncludedBadge item-name="active" :included="props.exportRecord.exportParams.includeFiles" />
            <IncludedBadge item-name="hidden" :included="props.exportRecord.exportParams.includeHidden" />
            <IncludedBadge item-name="deleted" :included="props.exportRecord.exportParams.includeDeleted" />
        </BCardText>
        <BCardText> <b>Stored in:</b> {{ props.exportRecord.importUri }} </BCardText>
    </BCard>
</template>
