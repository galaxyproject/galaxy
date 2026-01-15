<script setup lang="ts">
import {
    faCheckCircle,
    faCloudUploadAlt,
    faExclamationTriangle,
    faInfoCircle,
    faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import type { CardAction, CardBadge } from "@/components/Common/GCard.types";
import type { ExportRecord } from "@/components/Common/models/exportRecordModel";

import GCard from "@/components/Common/GCard.vue";

interface Props {
    /** The export record */
    exportRecord: ExportRecord;
    /** Whether to display the card in a grid view */
    gridView?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    gridView: false,
});

const emit = defineEmits<{
    (e: "onGoTo", to: string): void;
}>();

const objectType = computed(() => {
    const type = props.exportRecord.objectType;
    switch (type) {
        case "history":
            return "History";
        case "invocation":
            return "Workflow Invocation";
        default:
            return "Object";
    }
});

const objectId = computed(() => {
    return props.exportRecord.objectId;
});

const title = computed(() => {
    return `Export ${objectType.value} to File Source`;
});

const targetUri = computed(() => {
    return props.exportRecord.importUri || "Unknown destination";
});

const shortTargetUri = computed(() => {
    const uri = targetUri.value;
    // Extract just the filename from the URI
    const parts = uri.split("/");
    return parts[parts.length - 1] || uri;
});

const primaryActions = computed(() => {
    const actions: CardAction[] = [];

    if (objectId.value) {
        actions.push({
            id: "go-to-object",
            label: `Go to ${objectType.value}`,
            icon: faInfoCircle,
            title: `View details for ${objectType.value}`,
            variant: "outline-primary",
            handler: onGoToObject,
        });
    }

    return actions;
});

const badges = computed<CardBadge[]>(() => {
    const badges: CardBadge[] = [];

    if (props.exportRecord.isPreparing) {
        badges.push({
            id: "in-progress",
            title: "Export is in progress",
            label: "In Progress",
            variant: "info",
        });
    } else if (props.exportRecord.isReady) {
        badges.push({
            id: "completed",
            title: "Export completed successfully",
            label: "Complete",
            variant: "success",
        });
    } else if (props.exportRecord.hasFailed) {
        badges.push({
            id: "failed",
            label: "Failed",
            title: "Export failed",
            variant: "danger",
        });
    }

    return badges;
});

function onGoToObject() {
    const type = props.exportRecord.objectType;
    const id = objectId.value;
    if (!id) {
        return;
    }

    switch (type) {
        case "history":
            emit("onGoTo", `/histories/view?id=${id}`);
            break;
        case "invocation":
            emit("onGoTo", `/workflows/invocations/${id}`);
            break;
        default:
            console.warn(`No specific route defined for object type: ${type}`);
            break;
    }
}
</script>

<template>
    <GCard
        :id="exportRecord.id"
        class="remote-export-card"
        :title="title"
        :badges="badges"
        :primary-actions="primaryActions"
        :update-time="exportRecord.date.toISOString()"
        :grid-view="gridView"
        :title-icon="{
            icon: faCloudUploadAlt,
            title: 'Export to File Source',
        }">
        <template v-slot:description>
            <p class="text-muted mb-2"><strong>Destination:</strong> {{ shortTargetUri }}</p>
            <p v-if="exportRecord.modelStoreFormat" class="text-muted mb-2">
                <strong>Format:</strong> {{ exportRecord.modelStoreFormat }}
            </p>
            <BAlert v-if="exportRecord.isPreparing" variant="info" show>
                <FontAwesomeIcon :icon="faSpinner" spin />
                <span>Exporting to remote file source...</span>
            </BAlert>
            <BAlert v-if="exportRecord.isReady" variant="success" show>
                <FontAwesomeIcon :icon="faCheckCircle" />
                <span>Export completed successfully to {{ shortTargetUri }}</span>
            </BAlert>
            <BAlert v-if="exportRecord.hasFailed" variant="danger" show>
                <FontAwesomeIcon :icon="faExclamationTriangle" />
                <span>Export failed.</span>
                <span v-if="exportRecord.errorMessage"> <strong>Error:</strong> {{ exportRecord.errorMessage }} </span>
            </BAlert>
        </template>
    </GCard>
</template>
