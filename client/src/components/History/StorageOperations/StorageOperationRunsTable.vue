<script setup lang="ts">
import { faEye, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BPagination } from "bootstrap-vue";
import { computed } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import { useObjectStoreStore } from "@/stores/objectStoreStore";
import type { StorageRun } from "@/stores/storageOperationsStore";
import localize from "@/utils/localization";
import { isTerminalRunState } from "@/utils/storageOperations";
import { bytesToString } from "@/utils/utils";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import GTable from "@/components/Common/GTable.vue";
import Heading from "@/components/Common/Heading.vue";
import StorageOperationOutcomeProgress from "@/components/History/StorageOperations/StorageOperationOutcomeProgress.vue";
import StorageOperationRunStateBadge from "@/components/History/StorageOperations/StorageOperationRunStateBadge.vue";
import UtcDate from "@/components/UtcDate.vue";

type StorageOperationTableRow = StorageRun & {
    progressPercent: number;
};

interface Props {
    title: string;
    rows: StorageOperationTableRow[];
    currentPage: number;
    perPage: number;
    sortBy: string;
    sortDesc: boolean;
    emptyMessage: string;
    headingClass?: string;
    paginationClass?: string;
}

const props = withDefaults(defineProps<Props>(), {
    headingClass: undefined,
    paginationClass: undefined,
});

const emit = defineEmits<{
    (e: "sort-changed", sortBy: string, sortDesc: boolean): void;
    (e: "page-change", page: number): void;
    (e: "dismiss", runId: string): void;
}>();

const objectStoreStore = useObjectStoreStore();

const fields: TableField[] = [
    { key: "state", label: localize("Status"), sortable: true, width: "20px", align: "center" },
    { key: "mode", label: localize("Mode"), sortable: false, width: "80px" },
    { key: "target_object_store_id", label: localize("Target store"), sortable: true },
    { key: "total_count", label: localize("Datasets"), sortable: true, align: "center", width: "120px" },
    { key: "total_bytes_processed", label: localize("Data transferred"), sortable: true, width: "160px" },
    { key: "progressPercent", label: localize("Progress"), sortable: true, width: "220px" },
    { key: "create_time", label: localize("Started"), sortable: true, width: "180px" },
    { key: "update_time", label: localize("Completed"), sortable: true, width: "180px" },
    { key: "actions", label: localize("Actions"), sortable: false, width: "90px" },
];

const showPagination = computed(() => props.rows.length > props.perPage);

function onSortChanged(newSortBy: string, newSortDesc: boolean) {
    emit("sort-changed", newSortBy, newSortDesc);
}

function onPageChange(page: number) {
    emit("page-change", page);
}

function dismissStorageRun(runId: string) {
    emit("dismiss", runId);
}

function getTargetStoreDisplayName(targetObjectStoreId: string) {
    return objectStoreStore.getObjectStoreNameById(targetObjectStoreId) ?? targetObjectStoreId;
}

function formatDataCopied(totalBytesProcessed: number, succeededCount: number) {
    if (totalBytesProcessed === 0 && succeededCount > 0) {
        return localize("No data transfer required");
    }
    return bytesToString(totalBytesProcessed);
}
</script>

<template>
    <div>
        <Heading h3 size="sm" :class="props.headingClass">{{ props.title }}</Heading>

        <GTable
            striped
            hover
            stacked="md"
            show-empty
            :fields="fields"
            :items="props.rows"
            :current-page="props.currentPage"
            :per-page="props.perPage"
            :sort-by="props.sortBy"
            :sort-desc="props.sortDesc"
            :local-sorting="false"
            :local-filtering="false"
            :empty-state="{ message: props.emptyMessage }"
            @sort-changed="onSortChanged">
            <template v-slot:cell(state)="slot">
                <StorageOperationRunStateBadge
                    :state="slot.item.state"
                    :failed-count="slot.item.failed_count"
                    :skipped-count="slot.item.skipped_count" />
            </template>

            <template v-slot:cell(mode)="slot">
                <span class="text-monospace">{{ slot.item.mode }}</span>
            </template>

            <template v-slot:cell(target_object_store_id)="slot">
                {{ getTargetStoreDisplayName(slot.item.target_object_store_id) }}
            </template>

            <template v-slot:cell(total_bytes_processed)="slot">
                <span>{{ formatDataCopied(slot.item.total_bytes_processed, slot.item.succeeded_count) }}</span>
            </template>

            <template v-slot:cell(progressPercent)="slot">
                <StorageOperationOutcomeProgress
                    :total-count="slot.item.total_count"
                    :succeeded-count="slot.item.succeeded_count"
                    :failed-count="slot.item.failed_count"
                    :skipped-count="slot.item.skipped_count" />
            </template>

            <template v-slot:cell(create_time)="slot">
                <UtcDate :date="slot.item.create_time" mode="elapsed" />
            </template>

            <template v-slot:cell(update_time)="slot">
                <span v-if="isTerminalRunState(slot.item.state)">
                    <UtcDate :date="slot.item.update_time" mode="elapsed" />
                </span>
                <span v-else class="text-muted">—</span>
            </template>

            <template v-slot:cell(actions)="slot">
                <GButtonGroup aria-label="Actions">
                    <GButton
                        tooltip
                        tooltip-placement="bottom"
                        size="small"
                        color="blue"
                        outline
                        icon-only
                        :title="localize('View details')"
                        :to="slot.item.runUrl">
                        <FontAwesomeIcon :icon="faEye" fixed-width />
                    </GButton>
                    <GButton
                        tooltip
                        tooltip-placement="bottom"
                        size="small"
                        color="red"
                        outline
                        icon-only
                        :title="localize('Dismiss')"
                        @click.stop="dismissStorageRun(slot.item.run_id)">
                        <FontAwesomeIcon :icon="faTimes" fixed-width />
                    </GButton>
                </GButtonGroup>
            </template>
        </GTable>

        <div v-if="showPagination" class="d-flex justify-content-end" :class="props.paginationClass">
            <BPagination
                :value="props.currentPage"
                :total-rows="props.rows.length"
                :per-page="props.perPage"
                align="right"
                size="sm"
                first-number
                last-number
                @change="onPageChange" />
        </div>
    </div>
</template>
