<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { faFolder, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { RowClickEvent, RowSelectEvent, TableField } from "@/components/Common/GTable.types";
import { SELECTION_STATES, type SelectionItem } from "@/components/SelectionDialog/selectionTypes";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GTable from "@/components/Common/GTable.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

const LABEL_FIELD: TableField = { key: "label", label: "Name", sortable: true };
// GTable's local filter stringifies every item key; these hold no displayed text.
const FILTER_IGNORED_FIELDS = ["entry", "selectionState", "updateTime"];

interface Props {
    currentPage?: number;
    errorMessage?: string;
    fields?: TableField[];
    filter?: string;
    folderIcon?: IconDefinition;
    isBusy?: boolean;
    isEncoded?: boolean;
    items: SelectionItem[];
    leafIcon?: string;
    /** Let GTable filter, sort and page the items itself. */
    localPaging?: boolean;
    optionsShow?: boolean;
    perPage?: number;
    selectable?: boolean;
    /** Sorted field shown in the header; "" for none, unset for GTable's default. */
    sortBy?: string;
    sortDesc?: boolean;
    totalItems?: number;
}

const props = withDefaults(defineProps<Props>(), {
    currentPage: undefined,
    errorMessage: "",
    fields: () => [],
    filter: "",
    folderIcon: () => faFolder,
    isBusy: false,
    isEncoded: false,
    leafIcon: "fa fa-file-o",
    localPaging: false,
    optionsShow: false,
    perPage: undefined,
    selectable: false,
    sortBy: undefined,
    sortDesc: undefined,
    totalItems: 0,
});

const emit = defineEmits<{
    (e: "click", item: SelectionItem): void;
    (e: "open", item: SelectionItem): void;
    (e: "select-all", selected: boolean): void;
    (e: "sort-changed", sortBy: string, sortDesc: boolean): void;
}>();

const fieldDetails = computed<TableField[]>(() => {
    const fields: TableField[] = props.fields.slice().map((field) => ({
        ...field,
        sortable: field.sortable ?? true,
    }));
    if (fields.length === 0) {
        fields.unshift(LABEL_FIELD);
    }
    return fields;
});

/** GTable checkbox state from each item's selectionState: selected rows are checked, MIXED rows indeterminate. */
const selectedItems = computed(() => indexesWith(SELECTION_STATES.SELECTED));
const indeterminateItems = computed(() => indexesWith(SELECTION_STATES.MIXED));

function indexesWith(state: SelectionItem["selectionState"]): number[] {
    const indexes: number[] = [];
    props.items.forEach((item, index) => {
        if (item.selectionState === state) {
            indexes.push(index);
        }
    });
    return indexes;
}

function onRowClick(event: RowClickEvent<SelectionItem>) {
    // For a selectable table GTable also emits "row-select" on a row click
    // (handled by onRowSelect), so emitting here too would toggle selection
    // twice. Only emit for non-selectable dialogs.
    if (!props.selectable) {
        emit("click", event.item);
    }
}

// Selection for a selectable table: a row click and a checkbox toggle both
// arrive here as a single "row-select", so the checkbox behaves like the row.
function onRowSelect(event: RowSelectEvent<SelectionItem>) {
    emit("click", event.item);
}

function onSortChanged(sortBy: string, sortDesc: boolean) {
    emit("sort-changed", sortBy, sortDesc);
}

/** Format time stamp */
function formatTime(date?: Date) {
    if (date) {
        return date.toLocaleString("default", {
            day: "numeric",
            month: "short",
            year: "numeric",
            minute: "numeric",
            hour: "numeric",
        });
    } else {
        return "-";
    }
}
</script>

<template>
    <GAlert v-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </GAlert>
    <div v-else>
        <div v-if="optionsShow" data-description="selection dialog options">
            <GTable
                class="selection-dialog-table"
                clickable-rows
                compact
                hover
                primary-key="id"
                :current-page="localPaging ? currentPage : undefined"
                :fields="fieldDetails"
                :filter="filter"
                :filter-ignored-fields="FILTER_IGNORED_FIELDS"
                :items="items"
                :loading="isBusy"
                :local-filtering="localPaging"
                :local-sorting="localPaging"
                :indeterminate-items="indeterminateItems"
                :per-page="localPaging ? perPage : undefined"
                :selectable="selectable"
                :selected-items="selectedItems"
                :show-select-all="selectable"
                :sort-by="sortBy"
                :sort-desc="sortDesc"
                @row-click="onRowClick"
                @row-select="onRowSelect"
                @select-all="emit('select-all', $event)"
                @sort-changed="onSortChanged">
                <template v-slot:cell(label)="data">
                    <div style="cursor: pointer">
                        <pre
                            v-if="isEncoded"
                            :title="`label-${data.item.url}`"><code>{{ data.value ? data.value : "-" }}</code></pre>
                        <span v-else>
                            <div v-if="data.item.isLeaf">
                                <i :class="leafIcon" />
                                <span :title="`label-${data.item.url}`">{{ data.value ? data.value : "-" }}</span>
                            </div>
                            <button
                                v-else
                                type="button"
                                class="selection-dialog-folder"
                                :title="`label-${data.item.url}`"
                                @click.stop="emit('open', data.item)">
                                <FontAwesomeIcon :icon="folderIcon" />
                                {{ data.value ? data.value : "-" }}
                            </button>
                        </span>
                    </div>
                </template>

                <template v-slot:cell(details)="data">
                    <span :title="`details-${data.item.url}`">{{ data.value ? data.value : "-" }}</span>
                </template>

                <template v-slot:cell(tags)="data">
                    <StatelessTags v-if="data.value?.length > 0" :value="data.value" :disabled="true" />
                    <span v-else>-</span>
                </template>

                <template v-slot:cell(time)="data">
                    {{ formatTime(data.item.updateTime) }}
                </template>

                <template v-slot:cell(update_time)="data">
                    {{ formatTime(data.item.updateTime) }}
                </template>
            </GTable>

            <div v-if="isBusy" class="text-center" data-description="selection dialog busy spinners">
                <LoadingSpan />
            </div>
            <div v-else-if="totalItems === 0">
                <div v-if="filter">
                    No search results found for: <b> {{ filter }} </b>.
                </div>
                <div v-else>No entries.</div>
            </div>
        </div>
        <div v-else data-description="selection dialog spinner">
            <FontAwesomeIcon :icon="faSpinner" spin />
            <span>Please wait...</span>
        </div>
    </div>
</template>

<style scoped lang="scss">
.selection-dialog-folder {
    background: transparent;
    border: 0;
    padding: 0;
    min-height: 24px;
    text-align: left;
    color: var(--color-blue-700);
}
</style>
