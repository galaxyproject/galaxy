<script setup lang="ts">
import { storeToRefs } from "pinia";
import prettyBytes from "pretty-bytes";
import { useUserStore } from "@/stores/userStore";
import { formatDistanceToNowStrict } from "date-fns";
import { toRef, ref, computed, onMounted } from "vue";
import { useDetailedHistory } from "./usesDetailedHistory.js";
import { useConfig } from "@/composables/config";
import { HistoryFilters } from "@/components/History/HistoryFilters.js";
import PreferredStorePopover from "./PreferredStorePopover.vue";
import SelectPreferredStore from "./SelectPreferredStore.vue";

import { useRouter } from "vue-router/composables";

interface HistoryBase {
    id: string;
    preferred_object_store_id: string;
}

const props = withDefaults(
    defineProps<{
        history: HistoryBase;
        isWatching?: boolean;
        lastChecked: Date;
        filterText?: string;
        showControls?: boolean;
    }>(),
    {
        isWatching: false,
        lastChecked: () => new Date(),
        filterText: "",
        showControls: false,
    }
);

const router = useRouter();
const { config } = useConfig();
const { currentUser } = storeToRefs(useUserStore());
const { historySize, numItemsActive, numItemsDeleted, numItemsHidden } = useDetailedHistory(toRef(props, "history"));

const reloadButtonCls = ref("fa fa-sync");
const reloadButtonTitle = ref("");
const reloadButtonVariant = ref("link");
const showPreferredObjectStoreModal = ref(false);
const historyPreferredObjectStoreId = ref(props.history.preferred_object_store_id);

const niceHistorySize = computed(() => prettyBytes(historySize.value));

const emit = defineEmits(["update:filter-text", "reloadContents"]);

onMounted(() => {
    updateTime();
    // update every second
    setInterval(updateTime, 1000);
});

function onDashboard() {
    router.push({ name: "HistoryOverview", params: { historyId: props.history.id } });
}

function setFilter(filter: string) {
    let newFilterText = "";
    let settings = {};
    if (filter == "") {
        settings = {
            deleted: false,
            visible: true,
        };
    } else {
        const newVal = getCurrentFilterVal(filter) === "any" ? HistoryFilters.defaultFilters[filter] : "any";
        settings = {
            deleted: filter === "deleted" ? newVal : getCurrentFilterVal("deleted"),
            visible: filter === "visible" ? newVal : getCurrentFilterVal("visible"),
        };
    }
    newFilterText = HistoryFilters.applyFiltersToText(settings, props.filterText);
    emit("update:filter-text", newFilterText);
}

function getCurrentFilterVal(filter: string) {
    return HistoryFilters.getFilterValue(props.filterText, filter);
}

function updateTime() {
    const diffToNow = formatDistanceToNowStrict(props.lastChecked, { addSuffix: true });
    const diffToNowSec = Date.now().valueOf() - props.lastChecked.valueOf();
    // if history isn't being watched or hasn't been watched/polled for over 2 minutes
    if (!props.isWatching || diffToNowSec > 120000) {
        reloadButtonTitle.value = "Last refreshed " + diffToNow + ". Consider reloading the page.";
        reloadButtonVariant.value = "danger";
    } else {
        reloadButtonTitle.value = "Last refreshed " + diffToNow;
        reloadButtonVariant.value = "link";
    }
}

async function reloadContents() {
    emit("reloadContents");
    reloadButtonCls.value = "fa fa-sync fa-spin";
    setTimeout(() => {
        reloadButtonCls.value = "fa fa-sync";
    }, 1000);
}

function onUpdatePreferredObjectStoreId(preferredObjectStoreId: string) {
    showPreferredObjectStoreModal.value = false;
    // ideally this would be pushed back to the history object somehow
    // and tracked there... but for now this is only component using
    // this information.
    historyPreferredObjectStoreId.value = preferredObjectStoreId;
}
</script>

<template>
    <div class="history-size my-1 d-flex justify-content-between">
        <b-button
            v-b-tooltip.hover
            title="History Size"
            variant="link"
            size="sm"
            class="rounded-0 text-decoration-none history-storage-overview-button"
            :disabled="!showControls"
            data-description="storage dashboard button"
            @click="onDashboard">
            <icon icon="database" />
            <span>{{ niceHistorySize }}</span>
        </b-button>
        <b-button-group v-if="currentUser">
            <b-button
                v-if="config && config.object_store_allows_id_selection"
                :id="`history-storage-${history.id}`"
                title="Manage Preferred History Storage"
                variant="link"
                size="sm"
                class="rounded-0 text-decoration-none"
                @click="showPreferredObjectStoreModal = true">
                <icon icon="hdd" />
            </b-button>
            <PreferredStorePopover
                v-if="config && config.object_store_allows_id_selection"
                :history-id="history.id"
                :history-preferred-object-store-id="historyPreferredObjectStoreId"
                :user="currentUser">
            </PreferredStorePopover>
            <b-button-group>
                <b-button
                    v-b-tooltip.hover
                    title="Show active"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    data-description="show active items button"
                    @click="setFilter('')">
                    <span class="fa fa-map-marker" />
                    <span>{{ numItemsActive }}</span>
                </b-button>
                <b-button
                    v-if="numItemsDeleted"
                    v-b-tooltip.hover
                    title="Include deleted"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    :pressed="getCurrentFilterVal('deleted') !== false"
                    data-description="include deleted items button"
                    @click="setFilter('deleted')">
                    <icon icon="trash" />
                    <span>{{ numItemsDeleted }}</span>
                </b-button>
                <b-button
                    v-if="numItemsHidden"
                    v-b-tooltip.hover
                    title="Include hidden"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    :pressed="getCurrentFilterVal('visible') !== true"
                    data-description="include hidden items button"
                    @click="setFilter('visible')">
                    <icon icon="eye-slash" />
                    <span>{{ numItemsHidden }}</span>
                </b-button>
                <b-button
                    v-b-tooltip.hover
                    :title="reloadButtonTitle"
                    :variant="reloadButtonVariant"
                    size="sm"
                    class="rounded-0 text-decoration-none history-refresh-button"
                    @click="reloadContents()">
                    <span :class="reloadButtonCls" />
                </b-button>
            </b-button-group>
            <b-modal
                v-model="showPreferredObjectStoreModal"
                title="History Preferred Object Store"
                modal-class="history-preferred-object-store-modal"
                title-tag="h3"
                size="sm"
                hide-footer>
                <SelectPreferredStore
                    :user-preferred-object-store-id="currentUser.preferred_object_store_id"
                    :history="history"
                    @updated="onUpdatePreferredObjectStoreId" />
            </b-modal>
        </b-button-group>
    </div>
</template>
