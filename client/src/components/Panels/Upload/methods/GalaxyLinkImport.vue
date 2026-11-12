<script setup lang="ts">
import { computed, onUnmounted, ref, shallowRef, watch } from "vue";

import { GalaxyApi } from "@/api";
import {
    isLinkFromSource,
    isPickerCancel,
    isPickerHello,
    isPickerResult,
    makeNonce,
    parseSourceUrl,
    type SourceGalaxy,
} from "@/components/AnotherGalaxy/pickerProtocol";
import { useConfig } from "@/composables/config";
import { useTargetHistoryUploadState } from "@/composables/history/useTargetHistoryUploadState";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { errorMessageAsString } from "@/utils/simple-error";

import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GRadioGroup from "@/components/BaseComponents/GRadioGroup.vue";
import GSelect from "@/components/BaseComponents/GSelect.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import GalaxyLinkImportItem from "@/components/Panels/Upload/methods/GalaxyLinkImportItem.vue";

const props = defineProps<{
    method: { id: string };
    targetHistoryId: string;
}>();

const COULD_NOT_IMPORT =
    "The link could not be imported. It may have expired, or the other Galaxy may not have finished preparing it.";
const OTHER_SERVER = "other";
const RECENT_SERVERS_KEY = "galaxy-link-import-recent-servers";
const MAX_RECENT_SERVERS = 3;
const HELLO_NOTICE_DELAY = 15000;
const POPUP_CHECK_INTERVAL = 1000;

type Mode = "choose" | "paste";
type Notice = "blocked" | "no-answer" | "cancelled" | "bad-links" | "some-failed";

interface PickerSession {
    source: SourceGalaxy;
    nonce: string;
    popup: Window;
    historyId: string;
    /** The source's own root, from its hello; links must start with it. */
    root?: string;
}

interface ImportRow {
    id: number;
    name: string;
    taskId?: string;
    startError?: string;
}

const modeOptions = [
    { text: "Choose from another Galaxy", value: "choose" as Mode },
    { text: "Paste a link", value: "paste" as Mode },
];

const { config } = useConfig();

const { waitForTask, stopWaitingForTask, isRunning, isCompleted, hasFailed, failureReason, requestHasFailed } =
    useTaskMonitor();

const { uploadBlockReason } = useTargetHistoryUploadState(computed(() => props.targetHistoryId));

const mode = ref<Mode>("choose");
const link = ref("");
// The history the last import went to, which stays the same if the target is changed afterwards.
const importedHistoryId = ref<string>();
const isStarting = ref(false);
const startError = ref<string>();
const recentServers = ref<string[]>(readRecentServers());
const selectedServer = ref<string>();
const customUrl = ref("");
const session = shallowRef<PickerSession | null>(null);
const notice = ref<Notice>();
const noticeHost = ref("");
const failedCount = ref(0);
const importRows = ref<ImportRow[]>([]);
let nextRowId = 0;
let helloTimer: ReturnType<typeof setTimeout> | undefined;
let popupTimer: ReturnType<typeof setInterval> | undefined;

const trimmedLink = computed(() => link.value.trim());

const isWebLink = computed(() => /^https?:\/\//.test(trimmedLink.value));

const isImporting = computed(() => isStarting.value || isRunning.value);

const configuredServers = computed(() => {
    const entries: unknown = config.value?.another_galaxy_servers;
    if (!Array.isArray(entries)) {
        return [];
    }
    return entries.flatMap((entry) => {
        const source = parseSourceUrl(entry?.url);
        if (!source) {
            console.warn(
                `Ignoring the another_galaxy_servers entry "${entry?.label}": its url must use https, or http on localhost.`,
            );
            return [];
        }
        // This Galaxy is left out: choosing from itself is only possible by typing its address.
        return source.origin !== window.location.origin
            ? [{ text: String(entry.label || new URL(source.origin).host), value: source.root }]
            : [];
    });
});

const serverOptions = computed(() => {
    const configured = configuredServers.value;
    const recent = recentServers.value
        .filter((root) => !configured.some((option) => option.value === root))
        .map((root) => ({ text: root, value: root }));
    return [...configured, ...recent, { text: "Other Galaxy...", value: OTHER_SERVER }];
});

const isOtherServer = computed(() => selectedServer.value === OTHER_SERVER);

const source = computed(() => parseSourceUrl(isOtherServer.value ? customUrl.value : selectedServer.value));

const sourceHost = computed(() => (source.value ? new URL(source.value.origin).host : ""));

const showCustomUrlError = computed(() => isOtherServer.value && customUrl.value.trim() !== "" && !source.value);

const isWaiting = computed(() => Boolean(session.value));

// Clearing the link keeps a second click from importing the same items again.
watch(isCompleted, (completed) => {
    if (completed) {
        link.value = "";
    }
});

watch(
    serverOptions,
    (options) => {
        if (!options.some((option) => option.value === selectedServer.value)) {
            selectedServer.value = options[0]?.value;
        }
    },
    { immediate: true },
);

function readRecentServers(): string[] {
    try {
        const stored = JSON.parse(localStorage.getItem(RECENT_SERVERS_KEY) ?? "[]");
        return Array.isArray(stored)
            ? stored.flatMap((raw) => {
                  const parsed = parseSourceUrl(raw);
                  return parsed && parsed.root === raw ? [parsed.root] : [];
              })
            : [];
    } catch {
        return [];
    }
}

function rememberServer(root: string) {
    const recent = [root, ...recentServers.value.filter((other) => other !== root)].slice(0, MAX_RECENT_SERVERS);
    recentServers.value = recent;
    try {
        localStorage.setItem(RECENT_SERVERS_KEY, JSON.stringify(recent));
    } catch {
        // Not remembering the server only costs typing it again.
    }
}

async function onImport() {
    isStarting.value = true;
    startError.value = undefined;
    const historyId = props.targetHistoryId;
    try {
        const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/contents_from_store_async", {
            params: { path: { history_id: historyId } },
            body: { store_content_uri: trimmedLink.value, model_store_format: "tar.gz", discarded_data: "forbid" },
        });
        if (error) {
            startError.value = errorMessageAsString(error);
            return;
        }
        importedHistoryId.value = historyId;
        waitForTask(data.id, 3000);
    } catch (e) {
        startError.value = errorMessageAsString(e, COULD_NOT_IMPORT);
    } finally {
        isStarting.value = false;
    }
}

// Started here rather than in the row, so showing the rows again does not import the items again.
async function startRowImport(rowId: number, link: string, historyId: string) {
    const update = (patch: Partial<ImportRow>) => {
        const row = importRows.value.find((candidate) => candidate.id === rowId);
        if (row) {
            Object.assign(row, patch);
        }
    };
    try {
        const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/contents_from_store_async", {
            params: { path: { history_id: historyId } },
            body: { store_content_uri: link, model_store_format: "tar.gz", discarded_data: "forbid" },
        });
        if (error) {
            update({ startError: errorMessageAsString(error) });
            return;
        }
        update({ taskId: data.id });
    } catch (e) {
        update({ startError: errorMessageAsString(e, "The import could not be started.") });
    }
}

function endSession() {
    window.removeEventListener("message", onMessage);
    clearTimeout(helloTimer);
    clearInterval(popupTimer);
    session.value = null;
}

// The popup holds a reference to this window, so it is closed once it has answered, unless it lists failures to read.
function closePopup(popup: Window) {
    if (!popup.closed) {
        popup.close();
    }
}

function showNotice(kind: Notice, host: string) {
    notice.value = kind;
    noticeHost.value = host;
}

function onChoose() {
    const chosen = source.value;
    if (!chosen) {
        return;
    }
    endSession();
    notice.value = undefined;
    const nonce = makeNonce();
    const query = new URLSearchParams({ return: window.location.origin, nonce, hide_masthead: "true" });
    // Opened in the click itself, or the browser blocks it; without noopener, as the picker answers its opener.
    const popup = window.open(
        `${chosen.root}pick/another-galaxy?${query}`,
        "galaxy-picker",
        "popup,width=900,height=700",
    );
    const host = new URL(chosen.origin).host;
    if (!popup) {
        showNotice("blocked", host);
        return;
    }
    if (isOtherServer.value) {
        rememberServer(chosen.root);
    }
    session.value = { source: chosen, nonce, popup, historyId: props.targetHistoryId };
    window.addEventListener("message", onMessage);
    helloTimer = setTimeout(() => showNotice("no-answer", host), HELLO_NOTICE_DELAY);
    popupTimer = setInterval(() => {
        if (popup.closed) {
            // After a hello the picker worked, so closing its window is the same as Cancel.
            showNotice(session.value?.root ? "cancelled" : "no-answer", host);
            endSession();
        }
    }, POPUP_CHECK_INTERVAL);
}

function onMessage(event: MessageEvent) {
    const current = session.value;
    // Only the window this page opened, still showing the Galaxy it was opened on, may answer.
    if (!current || event.origin !== current.source.origin || event.source !== current.popup) {
        return;
    }
    const data: unknown = event.data;
    const host = new URL(current.source.origin).host;
    if (isPickerHello(data) && data.nonce === current.nonce) {
        // The picker knows its own root; a typed address may be a deeper page of the same Galaxy.
        const own = parseSourceUrl(data.root);
        if (own && own.origin === current.source.origin) {
            session.value = { ...current, root: own.root };
            clearTimeout(helloTimer);
            if (notice.value === "no-answer") {
                notice.value = undefined;
            }
        }
    } else if (isPickerResult(data) && data.nonce === current.nonce && current.root) {
        const root = current.root;
        endSession();
        // One foreign link means the picker is not behaving, so none of its links are used.
        const allFromSource = data.items.every((item) => isLinkFromSource(item.link, root));
        if (!allFromSource || data.failed === 0) {
            closePopup(current.popup);
        }
        if (!allFromSource) {
            showNotice("bad-links", host);
            return;
        }
        for (const item of data.items) {
            const id = nextRowId++;
            importRows.value.push({ id, name: item.name });
            startRowImport(id, item.link, current.historyId);
        }
        if (data.failed > 0) {
            failedCount.value = data.failed;
            showNotice("some-failed", host);
        }
    } else if (isPickerCancel(data) && data.nonce === current.nonce) {
        endSession();
        closePopup(current.popup);
        showNotice("cancelled", host);
    }
}

onUnmounted(() => {
    stopWaitingForTask();
    endSession();
});
</script>

<template>
    <div class="galaxy-link-import">
        <GRadioGroup
            v-model="mode"
            buttons
            class="mb-3"
            aria-label="How to import"
            data-description="galaxy link import mode"
            :options="modeOptions" />

        <template v-if="mode === 'choose'">
            <div class="mb-2">
                <label for="galaxy-picker-server">Galaxy server</label>
                <GSelect
                    id="galaxy-picker-server"
                    v-model="selectedServer"
                    data-description="galaxy picker server"
                    :options="serverOptions" />
            </div>

            <div v-if="isOtherServer" class="mb-2">
                <label for="galaxy-picker-url">Address of the other Galaxy</label>
                <GFormInput
                    id="galaxy-picker-url"
                    v-model="customUrl"
                    aria-describedby="galaxy-picker-url-help"
                    data-description="galaxy picker url"
                    placeholder="https://galaxy.example.org"
                    type="url"
                    :state="showCustomUrlError ? false : null" />
                <small id="galaxy-picker-url-help" class="form-text text-muted">
                    <template v-if="showCustomUrlError">
                        Enter a Galaxy address that starts with https://. Write international domain names in their xn--
                        form.
                    </template>
                    <template v-else-if="source">Opens {{ source.root }}</template>
                </small>
            </div>

            <GButton
                color="blue"
                data-description="galaxy picker open"
                :disabled="!source || Boolean(uploadBlockReason)"
                @click="onChoose">
                {{ sourceHost ? `Choose from ${sourceHost}` : "Choose from another Galaxy" }}
            </GButton>
            <small class="form-text text-muted">
                The other Galaxy must also run Galaxy 27.0 or newer. For older servers, use Paste a link.
            </small>

            <GAlert v-if="isWaiting" variant="info" class="mt-3" show data-description="galaxy picker waiting">
                <LoadingSpan
                    :message="
                        session?.root
                            ? `Choose the items in the ${sourceHost} window`
                            : `Waiting for ${sourceHost} to answer`
                    " />
            </GAlert>

            <GAlert
                v-if="notice === 'no-answer'"
                variant="warning"
                class="mt-3"
                show
                data-description="galaxy picker no answer">
                No answer from {{ noticeHost }} yet. If it shows "page not found", that Galaxy is too old: use Paste a
                link.
                <GButton size="small" class="ml-1" @click="mode = 'paste'">Paste a link</GButton>
            </GAlert>
            <GAlert
                v-else-if="notice === 'blocked'"
                variant="warning"
                class="mt-3"
                show
                data-description="galaxy picker blocked">
                Your browser blocked the window for {{ noticeHost }}. Allow pop-ups for this site and try again.
            </GAlert>
            <GAlert
                v-else-if="notice === 'bad-links'"
                variant="danger"
                class="mt-3"
                show
                data-description="galaxy picker bad links">
                {{ noticeHost }} sent links that do not belong to it, so nothing was imported.
            </GAlert>
            <GAlert
                v-else-if="notice === 'some-failed'"
                variant="warning"
                class="mt-3"
                show
                data-description="galaxy picker some failed">
                {{ failedCount === 1 ? "1 item" : `${failedCount} items` }} could not be exported on
                {{ noticeHost }} and did not arrive here. The {{ noticeHost }} window lists why.
            </GAlert>
            <GAlert
                v-else-if="notice === 'cancelled'"
                variant="info"
                class="mt-3"
                show
                data-description="galaxy picker cancelled">
                Nothing was chosen on {{ noticeHost }}.
            </GAlert>

            <ul v-if="importRows.length > 0" class="list-unstyled mt-3" data-description="galaxy picker imports">
                <GalaxyLinkImportItem
                    v-for="row in importRows"
                    :key="row.id"
                    :name="row.name"
                    :start-error="row.startError"
                    :task-id="row.taskId" />
            </ul>
        </template>
        <template v-else>
            <div class="mb-3">
                <label for="galaxy-link-input">Link from another Galaxy</label>
                <GFormInput
                    id="galaxy-link-input"
                    v-model="link"
                    aria-describedby="galaxy-link-help"
                    data-description="galaxy link input"
                    placeholder="https://usegalaxy.org/api/short_term_storage/..."
                    type="url"
                    :disabled="isImporting" />
                <small id="galaxy-link-help" class="form-text text-muted">
                    Made with Export to another Galaxy on the other server, which needs Galaxy 26.2 or newer.
                </small>
            </div>
            <GButton
                color="blue"
                data-description="galaxy link import"
                :disabled="!isWebLink || isImporting || Boolean(uploadBlockReason)"
                @click="onImport">
                Import
            </GButton>
            <GAlert v-if="isImporting" variant="info" class="mt-3" show>
                <LoadingSpan message="Importing into this history, this may take a while" />
            </GAlert>
            <GAlert v-else-if="startError" variant="danger" class="mt-3" show>{{ startError }}</GAlert>
            <GAlert v-else-if="hasFailed" variant="danger" class="mt-3" show>
                {{ COULD_NOT_IMPORT }}
                <div v-if="failureReason" class="mt-1 small">{{ failureReason }}</div>
            </GAlert>
            <GAlert v-else-if="requestHasFailed" variant="warning" class="mt-3" show>
                Galaxy could not check how the import is going. It may still finish, so look at the history before
                trying again.
            </GAlert>
            <GAlert v-else-if="isCompleted && importedHistoryId" variant="success" class="mt-3" show>
                Done! The items were imported into
                <SwitchToHistoryLink :history-id="importedHistoryId" :inline="true" :thin="false" />
            </GAlert>
        </template>
    </div>
</template>
