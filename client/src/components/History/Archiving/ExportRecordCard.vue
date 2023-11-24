<script setup lang="ts">
import { BCard, BCardText } from "bootstrap-vue";
import IncludedBadge from "./IncludedBadge.vue";
import type { ExportRecord } from "@/components/Common/models/exportRecordModel";

const props = defineProps<{
    exportRecord: ExportRecord;
}>();
</script>

<template>
    <b-card id="export-record-ready">
        <b-card-text>
            <b>Exported {{ props.exportRecord.elapsedTime }}</b> on {{ props.exportRecord.date }}
        </b-card-text>
        <b-card-text v-if="props.exportRecord.exportParams">
            <b>Contains datasets:</b>
            <IncludedBadge item-name="active" :included="props.exportRecord.exportParams.includeFiles" />
            <IncludedBadge item-name="hidden" :included="props.exportRecord.exportParams.includeHidden" />
            <IncludedBadge item-name="deleted" :included="props.exportRecord.exportParams.includeDeleted" />
        </b-card-text>
        <b-card-text> <b>Stored in:</b> {{ props.exportRecord.importUri }} </b-card-text>
    </b-card>
</template>
