<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDatabase, faEyeSlash, faHdd, faMapMarker, faSync, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchImmediate } from "@vueuse/core";
import { BButton, BButtonGroup, BModal } from "bootstrap-vue";
import { formatDistanceToNowStrict } from "date-fns";
import { storeToRefs } from "pinia";
import prettyBytes from "pretty-bytes";
import { computed, onMounted, ref, toRef } from "vue";
import { useRouter } from "vue-router/composables";

import { type HistorySummaryExtended, type RegisteredUser, userOwnsHistory } from "@/api";
import { HistoryFilters } from "@/components/History/HistoryFilters.js";
import { useConfig } from "@/composables/config";
import { useHistoryContentStats } from "@/composables/historyContentStats";
import { useStorageLocationConfiguration } from "@/composables/storageLocation";
import { useUserStore } from "@/stores/userStore";

import PreferredStorePopover from "./PreferredStorePopover.vue";
import SelectPreferredStore from "./SelectPreferredStore.vue";

const { isOnlyPreference } = useStorageLocationConfiguration();

library.add(faDatabase, faEyeSlash, faHdd, faMapMarker, faSync, faTrash);

const props = withDefaults(
    defineProps<{
        history: HistorySummaryExtended;
        isWatching?: boolean;
        lastChecked: Date;
        filterText?: string;
        showControls?: boolean;
        hideReload?: boolean;
    }>(),
    {
        isWatching: false,
        lastChecked: () => new Date(),
        filterText: "",
        showControls: false,
        hideReload: false,
    }
);

const emit = defineEmits(["update:filter-text", "reloadContents"]);

const router = useRouter();
const { config } = useConfig();
const { currentUser, isAnonymous } = storeToRefs(useUserStore());
const { historySize, numItemsActive, numItemsDeleted, numItemsHidden } = useHistoryContentStats(
    toRef(props, "history")
);

const reloadButtonLoading = ref(false);
const reloadButtonTitle = ref("");
const reloadButtonVariant = ref("link");
const showPreferredObjectStoreModal = ref(false);
const historyPreferredObjectStoreId = ref<string | null | undefined>();

watchImmediate(
    () => props.history,
    () => (historyPreferredObjectStoreId.value = props.history.preferred_object_store_id)
);

const niceHistorySize = computed(() => prettyBytes(historySize.value));
const canManageStorage = computed(
    () => userOwnsHistory(currentUser.value, props.history) && !currentUser.value?.isAnonymous
);

const storageLocationTitle = computed(() => {
    if (isOnlyPreference.value) {
        return "History Preferred Storage Location";
    } else {
        return "History Storage Location";
    }
});

function onDashboard() {
    router.push({ name: "HistoryOverviewInAnalysis", params: { historyId: props.history.id } });
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
    reloadButtonLoading.value = true;
    setTimeout(() => {
        reloadButtonLoading.value = false;
    }, 1000);
}

function onUpdatePreferredObjectStoreId(preferredObjectStoreId: string | null) {
    showPreferredObjectStoreModal.value = false;
    // ideally this would be pushed back to the history object somehow
    // and tracked there... but for now this is only component using
    // this information.
    historyPreferredObjectStoreId.value = preferredObjectStoreId;
}

const registeredUser = computed<RegisteredUser>(() => {
    if (isAnonymous.value) {
        throw new Error("Invalid anonymous user object encountered");
    }
    return currentUser.value as RegisteredUser;
});

onMounted(() => {
    updateTime();
    // update every second
    setInterval(updateTime, 1000);
});
</script>

<template>
    <div class="history-size my-1 d-flex justify-content-between">
        <BButton
            v-b-tooltip.hover
            title="History Size"
            variant="link"
            size="sm"
            class="rounded-0 text-decoration-none history-storage-overview-button"
            :disabled="!canManageStorage"
            data-description="storage dashboard button"
            @click="onDashboard">
            <FontAwesomeIcon :icon="faDatabase" />
            <span>{{ niceHistorySize }}</span>
        </BButton>

        <BButtonGroup v-if="currentUser">
            <BButton
                v-if="config && config.object_store_allows_id_selection && !isAnonymous"
                :id="`history-storage-${history.id}`"
                title="Manage Preferred History Storage"
                variant="link"
                size="sm"
                class="rounded-0 text-decoration-none"
                @click="showPreferredObjectStoreModal = true">
                <FontAwesomeIcon :icon="faHdd" />
            </BButton>

            <PreferredStorePopover
                v-if="config && config.object_store_allows_id_selection && !isAnonymous"
                :history-id="history.id"
                :history-preferred-object-store-id="historyPreferredObjectStoreId ?? undefined"
                :user="registeredUser">
            </PreferredStorePopover>

            <BButtonGroup>
                <BButton
                    v-b-tooltip.hover
                    title="Show active"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    data-description="show active items button"
                    @click="setFilter('')">
                    <FontAwesomeIcon :icon="faMapMarker" />
                    <span>{{ numItemsActive }}</span>
                </BButton>

                <BButton
                    v-if="numItemsDeleted"
                    v-b-tooltip.hover
                    title="Include deleted"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    :pressed="getCurrentFilterVal('deleted') !== false"
                    data-description="include deleted items button"
                    @click="setFilter('deleted')">
                    <FontAwesomeIcon :icon="faTrash" />
                    <span>{{ numItemsDeleted }}</span>
                </BButton>

                <BButton
                    v-if="numItemsHidden"
                    v-b-tooltip.hover
                    title="Include hidden"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    :pressed="getCurrentFilterVal('visible') !== true"
                    data-description="include hidden items button"
                    @click="setFilter('visible')">
                    <FontAwesomeIcon :icon="faEyeSlash" />
                    <span>{{ numItemsHidden }}</span>
                </BButton>

                <BButton
                    v-if="!hideReload"
                    v-b-tooltip.hover
                    :title="reloadButtonTitle"
                    :variant="reloadButtonVariant"
                    size="sm"
                    class="rounded-0 text-decoration-none history-refresh-button"
                    @click="reloadContents()">
                    <FontAwesomeIcon :icon="faSync" :spin="reloadButtonLoading" />
                </BButton>
            </BButtonGroup>

            <BModal
                v-model="showPreferredObjectStoreModal"
                :title="storageLocationTitle"
                modal-class="history-preferred-object-store-modal"
                title-tag="h3"
                size="sm"
                hide-footer>
                <SelectPreferredStore
                    v-if="!isAnonymous"
                    :user-preferred-object-store-id="registeredUser.preferred_object_store_id ?? undefined"
                    :history="history"
                    @updated="onUpdatePreferredObjectStoreId" />
            </BModal>
        </BButtonGroup>
    </div>
</template>

<style lang="scss" scoped>
.btn {
    white-space: nowrap;
}
</style>
