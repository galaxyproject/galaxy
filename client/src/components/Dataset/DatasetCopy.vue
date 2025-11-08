<script setup lang="ts">
import { faArrowRight, faCopy } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BFormCheckbox, BFormInput } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";
import Multiselect from "vue-multiselect";

import { GalaxyApi } from "@/api";

import LoadingSpan from "../LoadingSpan.vue";
import Heading from "@/components/Common/Heading.vue";

type HistoryItem = { id: string; name: string };
type SelectedPayload = { id: string; type: string };
type SourceEntry = { id: string; name: string; hid: number; type: string };

const errorMessage = ref("");
const histories = ref<HistoryItem[]>([]);
const loading = ref(true);
const newHistoryName = ref("");
const sourceContentSelection = ref<Record<string, boolean>>({});
const sourceContents = ref<SourceEntry[]>([]);
const sourceHistory = ref<HistoryItem | null>(null);
const successHistoryName = ref<string>("");
const successItemCount = ref<number>(0);
const successTargetIds = ref<Array<string>>([]);
const targetSingleHistory = ref<HistoryItem | null>(null);
const targetMultiSelections = ref<Record<string, boolean>>({});

const selectedContent = computed<SelectedPayload[]>(() => {
    const out: SelectedPayload[] = [];
    for (const item of sourceContents.value) {
        const key = `${item.type}|${item.id}`;
        if (sourceContentSelection.value[key]) {
            out.push({ id: item.id, type: item.type });
        }
    }
    return out;
});

const selectedTargets = computed<HistoryItem[]>(() => {
    if (newHistoryName.value) {
        return [];
    } else if (targetSingleHistory.value) {
        return [targetSingleHistory.value];
    } else {
        const out: HistoryItem[] = [];
        for (const h of histories.value) {
            if (targetMultiSelections.value[h.id]) {
                out.push(h);
            }
        }
        return out;
    }
});

async function loadHistories() {
    const { data, error } = await GalaxyApi().GET("/api/histories");
    if (error) {
        errorMessage.value = error.err_msg;
    } else if (Array.isArray(data)) {
        histories.value = data.map((h: any) => ({ id: h.id, name: h.name }));
        if (histories.value.length > 0) {
            const [first] = histories.value as [HistoryItem];
            sourceHistory.value = first;
            await loadContents();
        }
    } else {
        errorMessage.value = "No Histories found.";
    }
    loading.value = false;
}

async function loadContents() {
    loading.value = true;
    if (sourceHistory.value) {
        const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/contents", {
            params: { path: { history_id: sourceHistory.value.id } },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        } else if (Array.isArray(data)) {
            sourceContents.value = data.map((c: any) => ({
                id: c.id,
                name: c.name,
                hid: c.hid,
                type: c.history_content_type,
            }));
            const updated: Record<string, boolean> = {};
            for (const item of sourceContents.value) {
                updated[`${item.type}|${item.id}`] = false;
            }
            sourceContentSelection.value = updated;
        }
    }
    loading.value = false;
}

function toggleAll(v: boolean) {
    const updated: Record<string, boolean> = {};
    for (const key in sourceContentSelection.value) {
        updated[key] = v;
    }
    sourceContentSelection.value = updated;
}

async function onCopy() {
    errorMessage.value = "";
    successHistoryName.value = "";
    successItemCount.value = 0;
    successTargetIds.value = [];
    if (sourceHistory.value && selectedContent.value.length > 0) {
        loading.value = true;
        const targetIds = selectedTargets.value.map((h) => h.id);
        const { data, error } = await GalaxyApi().POST("/api/datasets/copy", {
            body: {
                source_history: sourceHistory.value.id,
                source_content: selectedContent.value,
                target_history_ids: newHistoryName.value ? [] : targetIds,
                target_history_name: newHistoryName.value || null,
            },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        } else if (data) {
            successItemCount.value = selectedContent.value.length;
            successHistoryName.value = newHistoryName.value;
            successTargetIds.value = data.history_ids;
            await loadContents();
        }
        loading.value = false;
    } else {
        errorMessage.value = "Please select Datasets and Collections.";
    }
}

onMounted(loadHistories);

defineExpose({
    sourceContentSelection,
    toggleAll,
});
</script>

<template>
    <div class="d-flex flex-column">
        <div>
            <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
            <BAlert v-else-if="successTargetIds.length > 0 && successTargetIds[0]" variant="success" show>
                {{ successItemCount }} item{{ successItemCount === 1 ? "" : "s" }} copied to
                <span v-if="successHistoryName">
                    <RouterLink
                        :to="`/histories/view?id=${successTargetIds[0]}`"
                        data-description="copy switch history">
                        {{ successHistoryName }}
                    </RouterLink>
                </span>
                <span v-else>
                    {{ successTargetIds.length }} histor{{ successTargetIds.length === 1 ? "y" : "ies" }}
                </span>
            </BAlert>
            <Heading h1 separator size="lg">Copy Datasets and Collections</Heading>
        </div>

        <div class="dataset-copy-columns d-flex flex-grow-1">
            <!-- Left column -->
            <div class="d-flex flex-column flex-grow-1 w-50 pr-1">
                <Heading h2 size="sm">
                    <FontAwesomeIcon :icon="faCopy" />
                    <span>From History</span>
                </Heading>
                <span class="text-sm mt-1">Select a Source History:</span>
                <Multiselect
                    v-model="sourceHistory"
                    :options="histories"
                    label="name"
                    track-by="id"
                    deselect-label=""
                    select-label=""
                    @input="loadContents" />
                <span class="text-sm mt-1">Select Datasets and Collections:</span>
                <div class="dataset-copy-contents flex-grow-1 overflow-auto border rounded p-2">
                    <LoadingSpan v-if="loading" />
                    <div v-else-if="sourceContents.length === 0" class="text-muted">This history has no datasets.</div>
                    <div v-else>
                        <div v-for="item in sourceContents" :key="item.id" class="d-flex align-items-center mb-1">
                            <BFormCheckbox
                                v-model="sourceContentSelection[`${item.type}|${item.id}`]"
                                :data-description="`copy ${item.type}|${item.id}`">
                                {{ item.hid }}: {{ item.name }}
                            </BFormCheckbox>
                        </div>
                    </div>
                </div>
                <div class="d-flex mt-2">
                    <BButton class="mr-2" size="sm" variant="outline-primary" @click="toggleAll(true)">
                        Select All
                    </BButton>
                    <BButton size="sm" variant="outline-primary" @click="toggleAll(false)"> Unselect All </BButton>
                </div>
            </div>

            <!-- Right column -->
            <div class="d-flex flex-column flex-grow-1 w-50 pl-1">
                <Heading h2 size="sm">
                    <FontAwesomeIcon :icon="faArrowRight" />
                    <span>To History</span>
                </Heading>
                <span class="text-sm mt-1">Select a Target History:</span>
                <Multiselect
                    v-model="targetSingleHistory"
                    :allow-empty="true"
                    :options="histories"
                    label="name"
                    track-by="id"
                    deselect-label=""
                    select-label=""
                    @input="
                        newHistoryName = '';
                        targetMultiSelections = {};
                    " />
                <span class="text-sm mt-1"><b>OR</b> Select Multiple Target Histories:</span>
                <div class="dataset-copy-contents flex-grow-1 overflow-auto border rounded p-2">
                    <div v-if="histories.length === 0" class="text-muted">There are no histories.</div>
                    <div v-for="h in histories" :key="h.id" class="d-flex align-items-center mb-1">
                        <BFormCheckbox
                            v-model="targetMultiSelections[h.id]"
                            @change="
                                newHistoryName = '';
                                targetSingleHistory = null;
                            ">
                            {{ h.name }}
                        </BFormCheckbox>
                    </div>
                </div>
                <span class="text-sm mt-1"><b>OR</b> Provide a New History Name:</span>
                <BFormInput
                    v-model="newHistoryName"
                    data-description="copy history name"
                    @input="
                        targetMultiSelections = {};
                        targetSingleHistory = null;
                    " />
                <div class="text-right mt-2">
                    <BButton
                        size="sm"
                        variant="primary"
                        :disabled="loading"
                        data-description="copy button"
                        @click="onCopy">
                        <FontAwesomeIcon :icon="faCopy" class="mr-1" />
                        <span v-localize>Copy Selected Items</span>
                    </BButton>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.dataset-copy-columns {
    min-height: 0;
}
.dataset-copy-contents {
    min-height: 10rem;
}
</style>
