<script setup lang="ts">
import { faCopy, faDatabase, faExchangeAlt, faEye, faGlobe, faUndo } from "font-awesome-6";
import { computed } from "vue";

import { type ArchivedHistorySummary } from "@/api/histories.archived";
import { type CardAttributes } from "@/components/Common/GCard.types";

import ExportRecordDOILink from "@/components/Common/ExportRecordDOILink.vue";
import GCard from "@/components/Common/GCard.vue";

interface Props {
    history: ArchivedHistorySummary;
}

const props = defineProps<Props>();

const canImportCopy = computed(() => props.history.export_record_data?.target_uri !== undefined);

const emit = defineEmits<{
    (e: "onView", history: ArchivedHistorySummary): void;
    (e: "onSwitch", history: ArchivedHistorySummary): void;
    (e: "onRestore", history: ArchivedHistorySummary): void;
    (e: "onImportCopy", history: ArchivedHistorySummary): void;
}>();

function onViewHistoryInCenterPanel() {
    emit("onView", props.history);
}

function onSetAsCurrentHistory() {
    emit("onSwitch", props.history);
}

async function onRestoreHistory() {
    emit("onRestore", props.history);
}

async function onImportCopy() {
    emit("onImportCopy", props.history);
}

const badges: CardAttributes[] = [
    {
        id: "published",
        label: "Published",
        title: "This history is published and can be viewed by others",
        icon: faGlobe,
        visible: props.history.published,
    },
    {
        id: "count",
        label: `${props.history.count} items`,
        title: "Amount of items in history",
        icon: faDatabase,
        visible: !props.history.purged,
    },
    {
        id: "snapshot",
        label: "Snapshot available",
        title: "This history has an associated export record containing a snapshot of the history that can be used to import a copy of the history.",
        icon: faCopy,
        visible: !!props.history.export_record_data,
    },
];

const secondaryActions: CardAttributes[] = [
    {
        id: "view",
        label: "View",
        icon: faEye,
        title: "View this history",
        handler: onViewHistoryInCenterPanel,
        visible: true,
    },
    {
        id: "switch",
        label: "Switch",
        icon: faExchangeAlt,
        title: "Set as current history",
        handler: onSetAsCurrentHistory,
        visible: true,
    },
];

const primaryActions: CardAttributes[] = [
    {
        id: "import-copy",
        label: "Import Copy",
        icon: faCopy,
        title: "Import a new copy of this history from the associated export record",
        disabled: !canImportCopy.value,
        variant: props.history.purged ? "primary" : "outline-primary",
        handler: onImportCopy,
        visible: canImportCopy.value,
    },
    {
        id: "restore",
        label: "Unarchive",
        icon: faUndo,
        title: "Unarchive this history and move it back to your active histories",
        variant: !props.history.purged ? "primary" : "outline-primary",
        handler: onRestoreHistory,
        visible: true,
    },
];
</script>

<template>
    <GCard
        :id="history.id"
        :title="history.name"
        :description="history.annotation || ''"
        :badges="badges"
        :secondary-actions="secondaryActions"
        :primary-actions="primaryActions"
        :update-time="history.update_time"
        update-time-title="Last edited/archived"
        :published="history.published"
        :tags="history.tags"
        :max-visible-tags="10">
        <template v-slot:titleActions>
            <ExportRecordDOILink :export-record-uri="history.export_record_data?.target_uri" />
        </template>
    </GCard>
</template>
