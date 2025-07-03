<script setup lang="ts">
import {
    faDownload,
    faHourglassEnd,
    faInfoCircle,
    faLink,
    faSpinner,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { formatDistanceToNow } from "date-fns";
import { computed, watch } from "vue";

import type { CardBadge } from "@/components/Common/GCard.types";
import type { MonitoringData, MonitoringRequest } from "@/composables/persistentProgressMonitor";
import { usePersistentProgressTaskMonitor } from "@/composables/persistentProgressMonitor";
import { useShortTermStorage } from "@/composables/shortTermStorage";
import { useShortTermStorageMonitor } from "@/composables/shortTermStorageMonitor";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { copy } from "@/utils/clipboard";
import { absPath } from "@/utils/redirect";
import { capitalizeFirstLetter } from "@/utils/strings";

import GCard from "@/components/Common/GCard.vue";

const { getDownloadObjectUrl } = useShortTermStorage();

interface Props {
    /** The monitoring data associated with the download request */
    monitoringData: MonitoringData;
    /** The ID of the task that needs to be updated */
    updateTaskId?: string;
    /** Whether to display the card in a grid view */
    gridView?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onGoTo", to: string): void;
    (e: "onDownload", url: string): void;
    (e: "onDelete", request: MonitoringRequest): void;
}>();

const title = computed(() => {
    return `${prettyAction.value} ${prettyObjectType.value} - ${
        props.monitoringData.request.object.name || "No name provided"
    }`;
});

const requestDateISO = computed(() => {
    return new Date(props.monitoringData.startedAt).toISOString();
});

const prettyObjectType = computed(() => {
    const type = props.monitoringData.request.object.type;
    switch (type) {
        case "history":
            return "History";
        case "invocation":
            return "Workflow Invocation";
        case "collection":
            return "Dataset Collection";
        default:
            return "Unknown Object Type";
    }
});

const prettyAction = computed(() => capitalizeFirstLetter(props.monitoringData.request.action));

const useMonitor = props.monitoringData.request.taskType === "task" ? useTaskMonitor() : useShortTermStorageMonitor();

const {
    isRunning,
    isCompleted,
    hasFailed,
    failureReason,
    requestHasFailed,
    storedTaskId,
    hasExpired,
    expirationDate,
    checkStatus,
    reset,
} = usePersistentProgressTaskMonitor(props.monitoringData.request, useMonitor);

const downloadUrl = computed(() => {
    // We can only download the result if the task type is short_term_storage.
    if (storedTaskId && props.monitoringData.request.taskType === "short_term_storage") {
        return getDownloadObjectUrl(storedTaskId);
    }
    return undefined;
});

const canDownload = computed(() => {
    return (
        isCompleted.value &&
        !hasExpired.value &&
        downloadUrl.value &&
        !requestHasFailed.value &&
        props.monitoringData.request.taskType === "short_term_storage"
    );
});

const primaryActions = computed(() => {
    const actions = [
        {
            id: "go-to-object",
            label: `Go to ${prettyObjectType.value}`,
            icon: faInfoCircle,
            title: `View details for ${prettyObjectType.value}`,
            variant: "outline-primary",
            handler: onGoToObject,
            visible: true,
        },
    ];

    if (canDownload.value) {
        actions.push({
            id: "copy-download-link",
            label: "Copy Link",
            icon: faLink,
            title: "Copy the download link to clipboard",
            variant: "outline-primary",
            handler: onCopyDownloadLink,
            visible: true,
        });
        actions.push({
            id: "download",
            label: "Download",
            icon: faDownload,
            title: "Download the result",
            variant: "primary",
            handler: onDownload,
            visible: true,
        });
    }

    if (hasFailed.value || hasExpired.value) {
        actions.push({
            id: "remove",
            label: "Remove",
            icon: faTrash,
            title: "Remove this record from the list",
            variant: "outline-danger",
            handler: onRemove,
            visible: true,
        });
    }

    return actions;
});

const elapsedTimeToExpire = computed(() =>
    expirationDate.value ? formatDistanceToNow(expirationDate.value, { addSuffix: true }) : undefined
);

const badges = computed<CardBadge[]>(() => {
    const badges: CardBadge[] = [];
    if (isRunning.value) {
        badges.push({
            id: "in-progress",
            title: `${prettyObjectType.value} is being prepared for download`,
            label: "In Progress",
            variant: "info",
            visible: true,
        });
    }
    if (canDownload.value) {
        badges.push({
            id: "ready-to-download",
            title: `Download ready for ${prettyObjectType.value}`,
            label: "Ready",
            variant: "success",
            visible: true,
        });
    }
    if (hasFailed.value) {
        badges.push({
            id: "failed-preparation",
            label: "Failed",
            title: `Failed to prepare ${prettyObjectType.value} for download`,
            variant: "danger",
            visible: true,
        });
    } else if (hasExpired.value) {
        badges.push({
            id: "download-request-expired",
            label: "Expired",
            title: `Download request for ${prettyObjectType.value} has expired`,
            variant: "warning",
            visible: true,
        });
    } else if (expirationDate.value && elapsedTimeToExpire.value) {
        badges.push({
            id: "expiration-date",
            label: `Expires ${elapsedTimeToExpire.value}`,
            title: `This download will expire on ${expirationDate.value.toLocaleString()}`,
            variant: "secondary",
            icon: faHourglassEnd,
            visible: true,
        });
    }
    return badges;
});

function onGoToObject() {
    const objectType = props.monitoringData.request.object.type;
    const objectId = props.monitoringData.request.object.id;
    switch (objectType) {
        case "history":
            emit("onGoTo", `/histories/view?id=${objectId}`);
            break;
        case "invocation":
            emit("onGoTo", `/workflows/invocations/${objectId}`);
            break;
        // case "collection": TODO use async route for collections
        default:
            console.warn(`No specific route defined for object type: ${objectType}`);
            break;
    }
}

function onDownload() {
    if (downloadUrl.value) {
        emit("onDownload", downloadUrl.value);
    } else {
        console.error("Download URL is not available.");
    }
}

function onCopyDownloadLink() {
    if (downloadUrl.value) {
        const link = absPath(downloadUrl.value);
        copy(link, `Download link for ${prettyObjectType.value} successfully copied to clipboard.`);
    } else {
        console.error("Download URL is not available for copying.");
    }
}

function onRemove() {
    emit("onDelete", props.monitoringData.request);
    reset();
}

// Instead of polling, watch for changes in the updateTaskId and if it matches the
// current taskId, trigger a status check.
watch(
    () => props.updateTaskId,
    (newTaskId) => {
        if (newTaskId === props.monitoringData.taskId) {
            checkStatus();
        }
    },
    { immediate: true }
);

// Initial check to set the status based on the currently stored monitoring data
// No request to the server is made here.
checkStatus({ enableFetch: false });
</script>
<template>
    <GCard
        :id="monitoringData.taskId"
        class="download-item-card"
        :title="title"
        :badges="badges"
        :primary-actions="primaryActions"
        :update-time="requestDateISO"
        :grid-view="gridView"
        :title-icon="{
            icon: faDownload,
            title: `${prettyAction} ${prettyObjectType}`,
        }">
        <template v-slot:description>
            <p v-if="monitoringData.request.description">
                {{ monitoringData.request.description }}
            </p>
            <BAlert v-if="isRunning" variant="info" show>
                <FontAwesomeIcon :icon="faSpinner" spin />
                <span>Preparing {{ prettyObjectType }} for download...</span>
            </BAlert>
            <BAlert v-if="hasFailed" variant="danger" show>
                The download request for {{ prettyObjectType }} has failed. Failure Reason:
                <strong>{{ failureReason }}</strong>
            </BAlert>
            <BAlert v-else-if="hasExpired" variant="warning" show>
                The download request has expired and the result is no longer available. You can go to the
                <strong>{{ prettyObjectType }}</strong> {{ monitoringData.request.action }} page and try again. This
                download record can now be removed from the list of recent downloads.
            </BAlert>
        </template>
    </GCard>
</template>
