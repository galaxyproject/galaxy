<script setup lang="ts">
import { BButton, BFormGroup, BModal } from "bootstrap-vue";
import { orderBy } from "lodash";
import isEqual from "lodash.isequal";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import type { HistorySummary } from "@/api";
import { HistoriesFilters } from "@/components/History/HistoriesFilters";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";

import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";
import HistoryList from "@/components/History/HistoryScrollList.vue";

type AdditionalOptions = "set-current" | "multi" | "center";
type PinnedHistory = { id: string };

interface Props {
    multiple?: boolean;
    title?: string;
    histories: HistorySummary[];
    additionalOptions?: AdditionalOptions[];
    showModal: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    multiple: false,
    title: "Switch to history",
    histories: () => [],
    additionalOptions: () => [],
    showModal: false,
});

const emit = defineEmits<{
    (e: "selectHistory", history: HistorySummary): void;
    (e: "selectHistories", histories: { id: string }[]): void;
    (e: "update:show-modal", showModal: boolean): void;
}>();

const propShowModal = computed({
    get: () => {
        return props.showModal;
    },
    set: (val: boolean) => {
        emit("update:show-modal", val);
    },
});

const selectedHistories = ref<PinnedHistory[]>([]);
const filter = ref("");
const busy = ref(false);
const showAdvanced = ref(false);
const modal = ref<BModal | null>(null);

const { pinnedHistories } = storeToRefs(useHistoryStore());

// retain previously selected histories when you reopen the modal in multi view
watch(
    () => propShowModal.value,
    (show: boolean) => {
        if (props.multiple && show) {
            selectedHistories.value = [...pinnedHistories.value];
        }
    },
    {
        immediate: true,
    }
);

/** if pinned histories and selected histories are equal */
const pinnedSelectedEqual = computed(() => {
    // uses `orderBy` to ensure same ids are found in both `{ id: string }[]` arrays
    return isEqual(orderBy(pinnedHistories.value, ["id"], ["asc"]), orderBy(selectedHistories.value, ["id"], ["asc"]));
});

function selectHistory(history: HistorySummary) {
    if (props.multiple) {
        const index = selectedHistories.value.findIndex((item: PinnedHistory) => item.id == history.id);
        if (index !== -1) {
            selectedHistories.value.splice(index, 1);
        } else {
            selectedHistories.value.push({ id: history.id });
        }
    } else {
        emit("selectHistory", history);
        modal.value?.hide();
    }
}

function selectHistories() {
    // set value of pinned histories in store
    emit("selectHistories", selectedHistories.value);
    // set local value equal to updated value from store
    selectedHistories.value = pinnedHistories.value;
    modal.value?.hide();
}

function setFilterValue(newFilter: string, newValue: string) {
    filter.value = HistoriesFilters.setFilterValue(filter.value, newFilter, newValue);
}

// hacky workaround for popovers in date pickers being cutoff
// https://github.com/galaxyproject/galaxy/issues/17711
const modalBodyClasses = computed(() => {
    return [
        "history-selector-modal-body",
        showAdvanced.value
            ? "history-selector-modal-body-allow-overflow"
            : "history-selector-modal-body-prevent-overflow",
    ];
});
</script>

<template>
    <div>
        <BModal
            ref="modal"
            v-model="propShowModal"
            content-class="history-selector-modal-content"
            v-bind="$attrs"
            :body-class="modalBodyClasses"
            static
            centered
            hide-footer
            v-on="$listeners">
            <template v-slot:modal-title>
                <Heading h2 inline size="sm">{{ localize(title) }}</Heading>
            </template>

            <BFormGroup :description="localize('Filter histories')">
                <FilterMenu
                    ref="filterMenuRef"
                    name="Histories"
                    placeholder="search histories"
                    :filter-class="HistoriesFilters"
                    :filter-text.sync="filter"
                    :loading="busy"
                    :show-advanced.sync="showAdvanced" />
            </BFormGroup>

            <HistoryList
                v-show="!showAdvanced"
                :multiple="props.multiple"
                :selected-histories="selectedHistories"
                :additional-options="props.additionalOptions"
                :show-modal.sync="propShowModal"
                in-modal
                :filter="filter"
                :loading.sync="busy"
                @selectHistory="selectHistory"
                @setFilter="setFilterValue">
                <template v-slot:modal-button-area>
                    <span class="d-flex align-items-center">
                        <a
                            v-if="multiple"
                            v-b-tooltip.noninteractive.hover
                            :title="localize('Click here to reset selection')"
                            class="mr-2"
                            href="javascript:void(0)"
                            @click="selectedHistories = []">
                            <i>{{ selectedHistories.length }} histories selected</i>
                        </a>
                        <BButton
                            v-if="multiple"
                            v-localize
                            data-description="change selected histories button"
                            :disabled="pinnedSelectedEqual || showAdvanced"
                            variant="primary"
                            @click="selectHistories">
                            Change Selected
                        </BButton>
                        <span v-else v-localize> Click a history to switch to it </span>
                    </span>
                </template>
            </HistoryList>
        </BModal>
    </div>
</template>

<style>
/** NOTE: Not using `<style scoped> here because these classes are
`BModal` `body-class` and `content-class` and so don't seem to work
with scoped or lang="scss" */

.history-selector-modal-body {
    display: flex;
    flex-direction: column;
}

.history-selector-modal-body-allow-overflow {
    overflow: visible;
}

.history-selector-modal-body-prevent-overflow {
    overflow: hidden;
}

.history-selector-modal-content {
    max-height: 80vh !important;
}
</style>
