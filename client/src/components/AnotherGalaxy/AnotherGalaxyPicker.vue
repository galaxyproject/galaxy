<script setup lang="ts">
import { faCopy } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchDebounced } from "@vueuse/core";
import { computed, type ComputedRef, onMounted, ref, shallowRef, watch } from "vue";

import { GalaxyApi, type HistoryItemSummary } from "@/api";
import { getContentItemState } from "@/components/History/Content/model/states";
import { useConfig } from "@/composables/config";
import { type ExportForAnotherGalaxyState, useExportForAnotherGalaxy } from "@/composables/exportForAnotherGalaxy";
import type { ExportableItem } from "@/stores/exportToAnotherGalaxyStore";
import { useHistoryStore } from "@/stores/historyStore";
import { copy as sendToClipboard } from "@/utils/clipboard";
import { formatDurationSeconds } from "@/utils/duration";
import { absPath } from "@/utils/redirect";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import {
    isPickerNonce,
    parseReturnOrigin,
    type PickedItem,
    PICKER_PROTOCOL,
    type PickerCancel,
    type PickerHello,
    type PickerResult,
} from "./pickerProtocol";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import GTable from "@/components/Common/GTable.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const PAGE_SIZE = 25;
const SEARCH_DELAY = 300;

const FIELDS = [
    { key: "selected", label: "Send" },
    { key: "name", label: "Name" },
    { key: "history_content_type", label: "Type" },
    { key: "history_id", label: "History" },
];

interface Props {
    /**
     * Ties the result to the request that opened the picker, from the `nonce` query parameter
     * @default undefined
     */
    nonce?: unknown;
    /**
     * Origin of the Galaxy that opened the picker, from the `return` query parameter
     * @default undefined
     */
    returnTo?: unknown;
}

const props = withDefaults(defineProps<Props>(), {
    nonce: undefined,
    returnTo: undefined,
});

interface Sent {
    item: ExportableItem;
    state: ComputedRef<ExportForAnotherGalaxyState>;
}

// Script only: the template would read __v_isRef on it, which throws for a cross-origin window.
const opener: Window | null = window.opener ?? null;
const hasOpener = Boolean(opener);

const { config, isConfigLoaded } = useConfig();
const historyStore = useHistoryStore();
const { start } = useExportForAnotherGalaxy();

const search = ref("");
const offset = ref(0);
const rows = ref<HistoryItemSummary[]>([]);
const total = ref(0);
const loading = ref(false);
const loadError = ref<string>();
const selected = ref(new Map<string, HistoryItemSummary>());
// Shallow, so the export states stay refs instead of being unwrapped.
const sent = shallowRef<Sent[]>([]);
const resultSent = ref(false);
const helloSent = ref(false);
const finished = ref(false);

const targetOrigin = computed(() => parseReturnOrigin(props.returnTo));

const nonce = computed(() => (isPickerNonce(props.nonce) ? props.nonce : null));

const canSend = computed(() => Boolean(targetOrigin.value && nonce.value));

const targetHost = computed(() => (targetOrigin.value ? new URL(targetOrigin.value).host : ""));

const canExport = computed(() => Boolean(config.value?.enable_celery_tasks));

const linkLifetime = computed(
    () => formatDurationSeconds(config.value?.short_term_storage_effective_duration) ?? "24 hours",
);

const selectedCount = computed(() => selected.value.size);

const itemsLabel = computed(() => (selectedCount.value === 1 ? "1 item" : `${selectedCount.value} items`));

const pageEnd = computed(() => Math.min(offset.value + rows.value.length, total.value));

const isSending = computed(() => sent.value.length > 0);

const allDone = computed(
    () => isSending.value && sent.value.every(({ state }) => ["ready", "failed"].includes(state.value.status)),
);

const readyItems = computed<PickedItem[]>(() =>
    sent.value.flatMap(({ item, state }) =>
        state.value.status === "ready" && state.value.link
            ? [{ type: item.contentType, name: item.contentName, link: state.value.link }]
            : [],
    ),
);

const failedItems = computed(() => sent.value.filter(({ state }) => state.value.status === "failed"));

// Dataset and collection ids can be equal, so the type is part of the key.
function keyOf(item: HistoryItemSummary) {
    return `${item.history_content_type}:${item.id}`;
}

// The same items the history panel offers to export: visible, not deleted, done and in an active history.
function pickBlockReason(item: HistoryItemSummary): string | undefined {
    if (!item.visible || item.deleted) {
        return "Hidden or deleted";
    }
    if (getContentItemState(item) !== "ok") {
        return "Not finished yet";
    }
    const history = historyStore.getHistoryById(item.history_id);
    if (!history) {
        return "Loading its history";
    }
    if (history.deleted) {
        return "In a deleted history";
    }
    if (history.archived) {
        return "In an archived history";
    }
    return undefined;
}

function canPick(item: HistoryItemSummary) {
    return pickBlockReason(item) === undefined;
}

function typeLabel(item: HistoryItemSummary) {
    return item.history_content_type === "dataset_collection" ? "Collection" : "Dataset";
}

function toggle(item: HistoryItemSummary, checked: boolean) {
    const next = new Map(selected.value);
    if (checked && canPick(item)) {
        next.set(keyOf(item), item);
    } else {
        next.delete(keyOf(item));
    }
    selected.value = next;
}

async function load() {
    loading.value = true;
    loadError.value = undefined;
    const term = search.value.trim();
    try {
        const { data, error, response } = await GalaxyApi().GET("/api/datasets", {
            params: {
                query: {
                    q: ["deleted", "visible", ...(term ? ["name-contains"] : [])],
                    qv: ["false", "true", ...(term ? [term] : [])],
                    limit: PAGE_SIZE,
                    offset: offset.value,
                    order: "update_time-dsc",
                    view: "summary",
                },
            },
        });
        if (error) {
            rethrowSimple(error);
        }
        rows.value = data as unknown as HistoryItemSummary[];
        total.value = parseInt(response.headers.get("total_matches") ?? "0", 10) || 0;
    } catch (e) {
        loadError.value = errorMessageAsString(e, "Your datasets and collections could not be loaded.");
    } finally {
        loading.value = false;
    }
}

function goToPage(newOffset: number) {
    offset.value = Math.max(0, newOffset);
    load();
}

function post(message: PickerHello | PickerResult | PickerCancel) {
    // Only ever to the exact origin that asked, so links never reach another site that took over the opener.
    if (opener && targetOrigin.value) {
        opener.postMessage(message, targetOrigin.value);
    }
}

function onSend() {
    if (!canSend.value || selectedCount.value === 0 || isSending.value) {
        return;
    }
    sent.value = Array.from(selected.value.values(), (row) => {
        const item: ExportableItem = {
            historyId: row.history_id,
            contentType: row.history_content_type,
            contentId: row.id,
            contentName: row.name || "",
        };
        return { item, state: start(item) };
    });
}

function onClose() {
    if (nonce.value && !resultSent.value) {
        post({ type: "galaxy-picker/cancel", nonce: nonce.value });
    }
    window.close();
}

function finish() {
    if (finished.value) {
        return;
    }
    finished.value = true;
    // A result with no items still reports the failures; otherwise Close would tell the target nothing was chosen.
    if (!opener || !nonce.value || (readyItems.value.length === 0 && failedItems.value.length === 0)) {
        return;
    }
    post({
        type: "galaxy-picker/result",
        protocol: PICKER_PROTOCOL,
        nonce: nonce.value,
        items: readyItems.value,
        failed: failedItems.value.length,
    });
    resultSent.value = true;
    if (failedItems.value.length === 0) {
        window.close();
    }
}

watch(
    isConfigLoaded,
    (loaded) => {
        if (loaded && !helloSent.value && nonce.value) {
            helloSent.value = true;
            post({
                type: "galaxy-picker/hello",
                protocol: PICKER_PROTOCOL,
                version: String(config.value?.version_major ?? ""),
                root: absPath("/"),
                nonce: nonce.value,
            });
        }
    },
    { immediate: true },
);

watch(allDone, (done) => {
    if (done) {
        finish();
    }
});

watchDebounced(
    search,
    () => {
        offset.value = 0;
        load();
    },
    { debounce: SEARCH_DELAY },
);

onMounted(() => {
    if (canSend.value) {
        load();
    }
});
</script>

<template>
    <div class="another-galaxy-picker p-3 h-100 overflow-auto">
        <Heading h1 size="lg">Choose items to send</Heading>

        <GAlert v-if="!canSend" variant="danger" show data-description="picker invalid request">
            This page was opened with a return address that is not a secure Galaxy address, so nothing can be sent from
            it. Close this window and try again from the other Galaxy.
        </GAlert>
        <LoadingSpan v-else-if="!isConfigLoaded" message="Loading" />
        <GAlert v-else-if="!canExport" variant="warning" show data-description="picker cannot export">
            This Galaxy cannot export items for another Galaxy. On {{ targetHost }}, use Paste a link with a link from a
            Galaxy that can.
        </GAlert>
        <template v-else-if="!isSending">
            <p>
                Tick the datasets and collections from your histories that you want to import into
                <b>{{ targetHost }}</b
                >.
            </p>

            <GAlert v-if="!hasOpener" variant="info" show data-description="picker no opener">
                This window is not connected to {{ targetHost }}, so the links will be shown here for you to copy and
                paste into its Import from Another Galaxy upload method.
            </GAlert>

            <label for="another-galaxy-picker-search" class="sr-only">Search by name</label>
            <GFormInput
                id="another-galaxy-picker-search"
                v-model="search"
                class="mb-2"
                data-description="picker search"
                placeholder="Search by name" />

            <GAlert v-if="loadError" variant="danger" show>{{ loadError }}</GAlert>

            <GTable
                compact
                show-empty
                :empty-state="{ message: 'No datasets or collections found' }"
                :fields="FIELDS"
                :items="rows"
                :loading="loading"
                :local-sorting="false">
                <template v-slot:cell(selected)="{ item }">
                    <GCheckbox
                        :aria-label="`Send ${item.name}`"
                        :data-description="`picker select ${keyOf(item)}`"
                        :disabled="!canPick(item)"
                        :model-value="selected.has(keyOf(item))"
                        :title="pickBlockReason(item)"
                        @update:model-value="(checked: boolean) => toggle(item, checked)" />
                </template>

                <template v-slot:cell(history_content_type)="{ item }">
                    {{ typeLabel(item) }}
                </template>

                <template v-slot:cell(history_id)="{ item }">
                    {{ historyStore.getHistoryNameById(item.history_id) }}
                </template>
            </GTable>

            <div v-if="total > PAGE_SIZE" class="d-flex align-items-center gap-1 mt-2">
                <GButton size="small" :disabled="offset === 0 || loading" @click="goToPage(offset - PAGE_SIZE)">
                    Previous
                </GButton>

                <span>{{ offset + 1 }}-{{ pageEnd }} of {{ total }}</span>

                <GButton size="small" :disabled="pageEnd >= total || loading" @click="goToPage(offset + PAGE_SIZE)">
                    Next
                </GButton>
            </div>

            <div class="another-galaxy-picker-consent mt-3 pt-3" data-description="picker consent">
                <p v-if="hasOpener">
                    Send {{ itemsLabel }} to <b>{{ targetHost }}</b
                    >. Anyone with these links can download the items without logging in until the links expire (usually
                    after {{ linkLifetime }}).
                </p>
                <p v-else>
                    Make links for {{ itemsLabel }}. Anyone with these links can download the items without logging in
                    until the links expire (usually after {{ linkLifetime }}).
                </p>

                <div class="d-flex gap-1">
                    <GButton data-description="picker cancel" @click="onClose">Cancel</GButton>

                    <GButton
                        color="blue"
                        data-description="picker send"
                        :disabled="selectedCount === 0"
                        @click="onSend">
                        {{ hasOpener ? `Send to ${targetHost}` : "Make links" }}
                    </GButton>
                </div>
            </div>
        </template>
        <template v-else>
            <ul class="list-unstyled" data-description="picker progress">
                <li v-for="{ item, state } in sent" :key="`${item.contentType}:${item.contentId}`" class="mb-2">
                    <b>{{ item.contentName }}</b>
                    <LoadingSpan
                        v-if="state.value.status === 'starting' || state.value.status === 'running'"
                        message="Preparing" />
                    <span v-else-if="state.value.status === 'failed'" class="text-danger">
                        Could not be exported: {{ state.value.error }}
                    </span>
                    <div v-else-if="!hasOpener" class="d-flex gap-1 mt-1">
                        <GFormInput
                            readonly
                            :aria-label="`Link for ${item.contentName}`"
                            data-description="picker link"
                            :model-value="state.value.link" />

                        <GButton
                            color="blue"
                            @click="sendToClipboard(state.value.link ?? '', 'Link copied to your clipboard')">
                            <FontAwesomeIcon :icon="faCopy" />
                            Copy
                        </GButton>
                    </div>
                    <span v-else class="text-success">Ready</span>
                </li>
            </ul>

            <template v-if="allDone">
                <GAlert v-if="hasOpener && readyItems.length > 0" variant="success" show data-description="picker sent">
                    Sent {{ readyItems.length === 1 ? "1 item" : `${readyItems.length} items` }} to {{ targetHost }}.
                    <span v-if="failedItems.length > 0">The items above that could not be exported were not sent.</span>
                </GAlert>
                <GAlert v-else-if="readyItems.length === 0" variant="danger" show data-description="picker none sent">
                    None of the items could be exported, so nothing was sent.
                </GAlert>

                <GButton data-description="picker close" @click="onClose">Close</GButton>
            </template>
        </template>
    </div>
</template>

<style scoped lang="scss">
.another-galaxy-picker-consent {
    border-top: 1px solid var(--color-grey-300);
}
</style>
