<script setup lang="ts">
import { formatDistanceToNowStrict } from "date-fns";
import { computed, onMounted, onUnmounted, reactive, ref, type PropType, type Ref } from "vue";
import { useRouter } from "vue-router/composables";
import PreferredStorePopover from "./PreferredStorePopover.vue";
import SelectPreferredStore from "./SelectPreferredStore.vue";
import { bytesToString, randomRange } from "@/utils/utils";
import { useCurrentUser } from "@/composables/user";
import { useConfig } from "@/composables/config";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEyeSlash, faMapMarker, faTrash, faSync, faDatabase, faHdd } from "@fortawesome/free-solid-svg-icons";

interface History {
    size: number;
    contents_active?: {
        active: number;
        deleted: number;
        hidden: number;
    };
    id: string;
    preferred_object_store_id: string;
}

/** @ts-ignore bad library types */
library.add(faEyeSlash, faMapMarker, faTrash, faSync, faDatabase, faHdd);

const props = defineProps({
    history: { type: Object as PropType<History>, required: true },
    isWatching: { type: Boolean, default: false },
    lastChecked: { type: Date, default: null },
});

const emit = defineEmits<{
    (e: "update:filter-text", newFilterText: string): void;
    (e: "reloadContents"): void;
}>();

const router = useRouter();
const { config } = useConfig(true);
const { currentUser } = useCurrentUser(true);

const prettyTotalHistorySize = computed(() => bytesToString(props.history.size, true, 2));
const numItemsActive = computed(() => props.history.contents_active?.active ?? 0);
const numItemsDeleted = computed(() => props.history.contents_active?.deleted ?? 0);
const numItemsHidden = computed(() => props.history.contents_active?.hidden ?? 0);

const showPreferredObjectStoreModal = ref(false);
const historyPreferredObjectStoreId: Ref<string | null> = ref(props.history.preferred_object_store_id);

function setFilter(filter: string) {
    emit("update:filter-text", filter);
}

function onUpdatePreferredObjectStoreId(preferredObjectStoreId: string | null) {
    showPreferredObjectStoreModal.value = false;
    // ideally this would be pushed back to the history object somehow
    // and tracked there... but for now this is only component using
    // this information.
    historyPreferredObjectStoreId.value = preferredObjectStoreId;
}

const reloadButton = reactive({
    title: "",
    variant: "link",
    spin: false,
});

function reloadContents() {
    emit("reloadContents");
    reloadButton.spin = true;

    setTimeout(() => {
        reloadButton.spin = false;
    }, randomRange(800, 1400));
}

function updateTime() {
    const diffToNow = formatDistanceToNowStrict(props.lastChecked, { addSuffix: true });
    const diffToNowSec = Date.now() - props.lastChecked.getTime();
    // if history isn't being watched or hasn't been watched/polled for over 2 minutes
    if (!props.isWatching || diffToNowSec > 120000) {
        reloadButton.title = "Last refreshed " + diffToNow + ". Consider reloading the page.";
        reloadButton.variant = "danger";
    } else {
        reloadButton.title = "Last refreshed " + diffToNow;
        reloadButton.variant = "link";
    }
}

let interval: ReturnType<typeof setInterval> | undefined;

onMounted(() => {
    updateTime();
    interval = setInterval(updateTime, 1000);
});

onUnmounted(() => {
    if (interval) {
        clearInterval(interval);
    }
});
</script>

<template>
    <div class="history-size my-1 d-flex justify-content-between">
        <b-button
            v-b-tooltip.hover
            title="History Size"
            variant="link"
            size="sm"
            class="rounded-0 text-decoration-none"
            @click="() => router.push('/storage')">
            <FontAwesomeIcon icon="fa-database" />
            <span>{{ prettyTotalHistorySize }}</span>
        </b-button>
        <b-button-group>
            <b-button
                v-if="config && config.object_store_allows_id_selection"
                :id="`history-storage-${history.id}`"
                variant="link"
                size="sm"
                class="rounded-0 text-decoration-none"
                @click="() => (showPreferredObjectStoreModal = true)">
                <FontAwesomeIcon icon="fa-hdd" />
            </b-button>
            <PreferredStorePopover
                v-if="config && config.object_store_allows_id_selection"
                :history-id="history.id"
                :history-preferred-object-store-id="historyPreferredObjectStoreId ?? undefined"
                :user="currentUser">
            </PreferredStorePopover>
            <b-button-group>
                <b-button
                    v-b-tooltip.hover
                    title="Show active"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    @click="() => setFilter('')">
                    <FontAwesomeIcon class="fa-map-marker" />
                    <span>{{ numItemsActive }}</span>
                </b-button>
                <b-button
                    v-if="numItemsDeleted"
                    v-b-tooltip.hover
                    title="Show deleted"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    @click="() => setFilter('deleted:true')">
                    <FontAwesomeIcon icon="fa-trash" />
                    <span>{{ numItemsDeleted }}</span>
                </b-button>
                <b-button
                    v-if="numItemsHidden"
                    v-b-tooltip.hover
                    title="Show hidden"
                    variant="link"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    @click="() => setFilter('visible:false')">
                    <FontAwesomeIcon icon="fa-eye-slash" />
                    <span>{{ numItemsHidden }}</span>
                </b-button>
                <b-button
                    v-b-tooltip.hover
                    :title="reloadButton.title"
                    :variant="reloadButton.variant"
                    size="sm"
                    class="rounded-0 text-decoration-none"
                    @click="reloadContents">
                    <FontAwesomeIcon icon="fa-sync" :spin="reloadButton.spin" />
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
                    :user-preferred-object-store-id="currentUser?.preferred_object_store_id"
                    :history="history"
                    @updated="onUpdatePreferredObjectStoreId" />
            </b-modal>
        </b-button-group>
    </div>
</template>
