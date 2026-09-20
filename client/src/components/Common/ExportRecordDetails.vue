<script setup lang="ts">
import {
    faCheckCircle,
    faDownload,
    faExclamationCircle,
    faExclamationTriangle,
    faFileImport,
    faHourglassEnd,
    faLink,
    faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import type { ColorVariant } from "@/components/Common";
import type { CardAction, CardBadge } from "@/components/Common/GCard.types";
import type { ExportRecord } from "@/components/Common/models/exportRecordModel";

import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";

interface Props {
    record: ExportRecord;
    objectType: string;
    actionMessage?: string;
    actionMessageVariant?: ColorVariant;
}

const props = withDefaults(defineProps<Props>(), {
    actionMessage: undefined,
    actionMessageVariant: "info",
});

const emit = defineEmits<{
    (e: "onActionMessageDismissed"): void;
    (e: "onReimport", record: ExportRecord): void;
    (e: "onDownload", record: ExportRecord): void;
    (e: "onCopyDownloadLink", record: ExportRecord): void;
}>();

const primaryActions = computed<CardAction[]>(() => {
    const actions: CardAction[] = [];

    if (props.record.canDownload) {
        actions.push({
            id: "copy-download-link",
            label: "Copy Link",
            icon: faLink,
            title: "Copy the download link to clipboard",
            variant: "outline-primary",
            handler: () => emit("onCopyDownloadLink", props.record),
        });
        actions.push({
            id: "download",
            label: "Download",
            icon: faDownload,
            title: "Download the result",
            variant: "primary",
            handler: () => emit("onDownload", props.record),
        });
    }

    if (props.record.canReimport) {
        actions.push({
            id: "reimport",
            label: "Reimport",
            icon: faFileImport,
            title: `Reimport the ${props.objectType} from this export record`,
            variant: "primary",
            handler: () => emit("onReimport", props.record),
        });
    }

    return actions;
});

const badges = computed<CardBadge[]>(() => {
    const badges: CardBadge[] = [];
    if (props.record.isPreparing) {
        badges.push({
            id: "in-progress",
            title: `${props.objectType} is being prepared for download`,
            label: "In Progress",
            variant: "info",
        });
    }
    if (props.record.canDownload) {
        badges.push({
            id: "ready-to-download",
            title: `${props.objectType} is ready to download`,
            label: "Ready to Download",
            variant: "success",
        });
    }
    if (props.record.hasFailed) {
        badges.push({
            id: "failed",
            title: `Failed to prepare ${props.objectType} for download`,
            label: "Failed",
            variant: "danger",
        });
    } else if (props.record.canExpire) {
        if (props.record.hasExpired) {
            badges.push({
                id: "expired",
                title: `The ${props.objectType} has expired and can no longer be downloaded. Please generate a new export.`,
                label: "Expired",
                variant: "warning",
                icon: faHourglassEnd,
            });
        } else {
            badges.push({
                id: "expires-soon",
                label: `Expires ${props.record.expirationElapsedTime}`,
                title: `The ${props.objectType} was exported ${props.record.elapsedTime} and this download link will expire in ${props.record.expirationElapsedTime}`,
                variant: "warning",
                icon: faHourglassEnd,
            });
        }
    }
    return badges;
});

function onMessageDismissed() {
    emit("onActionMessageDismissed");
}
</script>

<template>
    <GCard id="latest-export-record" class="export-record-details" :primary-actions="primaryActions" :badges="badges">
        <template v-slot:title>
            <Heading h3 size="sm">
                <span v-if="props.record.isPreparing">
                    <FontAwesomeIcon :icon="faSpinner" spin class="mr-1" />
                    Preparing {{ props.objectType }} for download...
                </span>
                <span v-else>
                    This {{ props.objectType }} was exported <b>{{ props.record.elapsedTime }}</b>
                </span>
            </Heading>
        </template>
        <template v-slot:description>
            <span v-if="props.record.hasFailed">
                <FontAwesomeIcon
                    :icon="faExclamationCircle"
                    class="text-danger record-failed-icon"
                    title="Export failed" />

                <span>
                    Something failed during the export process. Please try again and if the problem persist contact your
                    administrator.
                </span>

                <BAlert :show="props.record.errorMessage" variant="danger">{{ props.record.errorMessage }}</BAlert>
            </span>
            <span v-if="props.record.isUpToDate" title="Up to date">
                <FontAwesomeIcon :icon="faCheckCircle" class="text-success record-up-to-date-icon" />
                <span>
                    This export record contains the latest changes of the {{ props.objectType }} in
                    <b class="record-archive-format">{{ props.record.modelStoreFormat }}</b> format.
                </span>
            </span>
            <span v-else>
                <FontAwesomeIcon :icon="faExclamationTriangle" class="text-warning record-outdated-icon" />
                <span>
                    This export is outdated and contains the changes of this {{ props.objectType }} from
                    {{ props.record.elapsedTime }}.
                </span>
            </span>

            <span v-if="props.record.canExpire" class="mt-3">
                <span v-if="props.record.hasExpired">
                    <FontAwesomeIcon :icon="faHourglassEnd" class="text-danger record-expired-icon" />
                    This download link has expired, and the result is no longer available. You can generate a new export
                    before downloading it again.
                </span>
                <span v-else>
                    <FontAwesomeIcon :icon="faHourglassEnd" class="text-warning record-expiration-warning-icon" />
                    This download link expires {{ props.record.expirationElapsedTime }}.
                </span>
            </span>

            <BAlert
                v-if="props.actionMessage !== undefined"
                :variant="props.actionMessageVariant"
                show
                fade
                dismissible
                @dismissed="onMessageDismissed">
                {{ props.actionMessage }}
            </BAlert>
        </template>
    </GCard>
</template>
