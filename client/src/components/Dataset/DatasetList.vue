<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { GalaxyApi, type HDASummary } from "@/api";
import { copyDataset } from "@/api/datasets";
import { updateTags } from "@/api/tags";
import { useHistoryStore } from "@/stores/historyStore";
import { rethrowSimple } from "@/utils/simple-error";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import GTable from "@/components/Common/GTable.vue";
import DatasetName from "@/components/Dataset/DatasetName.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const query = ref("");
const limit = ref(50);
const offset = ref(0);
const message = ref("");
const loading = ref(true);
const sortDesc = ref(true);
const sortBy = ref("update_time");
const rows = ref<HDASummary[]>([]);
const messageVariant = ref("danger");
const fields = [
    {
        key: "name",
        label: "Name",
        sortable: true,
    },
    {
        key: "tags",
        label: "Tags",
        sortable: false,
    },
    {
        key: "history_id",
        label: "History",
        sortable: true,
    },
    {
        key: "extension",
        label: "Extension",
        sortable: true,
    },
    {
        key: "update_time",
        label: "Updated",
        sortable: true,
    },
    {
        key: "context",
        label: "",
        sortable: false,
    },
];

const showNotFound = computed(() => {
    return !loading.value && rows.value.length === 0 && query;
});
const showNotAvailable = computed(() => {
    return !loading.value && rows.value.length === 0 && !query.value;
});

async function load(concat = false) {
    loading.value = true;

    try {
        const { data, error } = await GalaxyApi().GET("/api/datasets", {
            params: {
                query: {
                    q: ["name-contains"],
                    qv: [query.value],
                    limit: limit.value,
                    offset: offset.value,
                    order: `${sortBy.value}${sortDesc.value ? "-dsc" : "-asc"}`,
                    view: "summary",
                },
            },
        });

        if (error) {
            rethrowSimple(error);
        }

        const datasets = data as HDASummary[];

        if (concat) {
            rows.value = rows.value.concat(datasets);
        } else {
            rows.value = datasets;
        }
    } catch (error: any) {
        onError(error);
    } finally {
        loading.value = false;
    }
}

async function onCopyDataset(item: HDASummary) {
    const dataset_id = item.id;

    try {
        if (!currentHistoryId.value) {
            throw new Error("No current history found.");
        }

        await copyDataset(dataset_id, currentHistoryId.value);

        historyStore.loadCurrentHistory();
    } catch (error: any) {
        onError(error);
    }
}

async function onShowDataset(item: HDASummary) {
    const { history_id } = item;
    const filters = {
        deleted: item.deleted,
        visible: item.visible,
        hid: item.hid,
    };

    try {
        await historyStore.applyFilters(history_id, filters);
    } catch (error: any) {
        onError(error);
    }
}

async function onTags(tags: string[], index: number) {
    const item = rows.value[index];

    if (item) {
        item.tags = tags;
    }

    try {
        await updateTags(item?.id as string, "HistoryDatasetAssociation", tags);
    } catch (error: any) {
        onError(error);
    }
}

function onQuery(q: string) {
    query.value = q;
    offset.value = 0;

    load();
}

function onSort(event: { sortBy: string; sortDesc: boolean }) {
    offset.value = 0;
    sortBy.value = event.sortBy;
    sortDesc.value = event.sortDesc;

    load();
}

function onScroll(scroll: Event) {
    const { scrollTop, clientHeight, scrollHeight } = scroll.target as HTMLElement;

    if (scrollTop + clientHeight >= scrollHeight) {
        if (offset.value + limit.value <= rows.value.length) {
            offset.value += limit.value;

            load(true);
        }
    }
}

function onError(msg: string) {
    message.value = msg;
}

onMounted(() => {
    load();
});
</script>

<template>
    <div class="overflow-auto h-100" @scroll="onScroll">
        <BAlert v-if="message" :variant="messageVariant" show>
            {{ message }}
        </BAlert>

        <DelayedInput class="m-1 mb-3" placeholder="Search Datasets" @change="onQuery" />

        <GTable
            id="dataset-table"
            striped
            no-sort-reset
            no-local-sorting
            :fields="fields"
            :items="rows"
            :sort-by="sortBy"
            :sort-desc="sortDesc"
            :loading="loading"
            loading-message="Loading datasets"
            :empty-state="{
                message: showNotFound
                    ? `No matching entries found for: ${query}`
                    : showNotAvailable
                      ? 'No datasets found.'
                      : 'Loading...',
                variant: 'info',
            }"
            @sort-changed="onSort">
            <template v-slot:cell(name)="row">
                <DatasetName :item="row.item" @showDataset="onShowDataset" @copyDataset="onCopyDataset" />
            </template>

            <template v-slot:cell(history_id)="row">
                <SwitchToHistoryLink
                    :history-id="row.item.history_id"
                    :filters="{ deleted: row.item.deleted, visible: row.item.visible, hid: row.item.hid }" />
            </template>

            <template v-slot:cell(tags)="row">
                <StatelessTags
                    :value="row.item.tags"
                    :disabled="row.item.deleted"
                    @input="(tags) => onTags(tags, row.index)" />
            </template>

            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
        </GTable>
    </div>
</template>
