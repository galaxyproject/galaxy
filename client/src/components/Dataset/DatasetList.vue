<script setup lang="ts">
import { BAlert, BTable } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { GalaxyApi, type HDASummary } from "@/api";
import { copyDataset } from "@/api/datasets";
import { updateTags } from "@/api/tags";
import { useHistoryStore } from "@/stores/historyStore";
import { rethrowSimple } from "@/utils/simple-error";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import DatasetName from "@/components/Dataset/DatasetName.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
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
const fields = ref([
    {
        key: "name",
        sortable: true,
    },
    {
        key: "tags",
        sortable: false,
    },
    {
        label: "History",
        key: "history_id",
        sortable: true,
    },
    {
        key: "extension",
        sortable: true,
    },
    {
        label: "Updated",
        key: "update_time",
        sortable: true,
    },
    {
        key: "context",
        label: "",
        sortable: false,
    },
]);

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

function onSort(props: { sortBy: string; sortDesc: boolean }) {
    offset.value = 0;
    sortBy.value = props.sortBy;
    sortDesc.value = props.sortDesc;

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

        <BTable
            id="dataset-table"
            striped
            no-sort-reset
            no-local-sorting
            :fields="fields"
            :items="rows"
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
        </BTable>

        <LoadingSpan v-if="loading" message="Loading datasets" />

        <BAlert v-if="showNotFound" variant="info" show>
            No matching entries found for: <span class="font-weight-bold">{{ query }}</span>
        </BAlert>

        <BAlert v-if="showNotAvailable" variant="info" show> No datasets found. </BAlert>
    </div>
</template>
