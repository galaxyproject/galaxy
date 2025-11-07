<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, ref } from "vue";

const loading = ref(false);
const error = ref("");
const done = ref("");
const histories = ref<Array<{ id: string; name: string }>>([]);

const sourceHistoryId = ref<string | null>(null);
const targetSingleId = ref<string | null>(null);
const targetMultiIds = ref<Record<string, boolean>>({});
const newHistoryName = ref("");
const useMultipleTargets = ref(false);

const sourceContents = ref<Array<{ id: string; name: string; hid: number; type: string }>>([]);
const sourceContentSelection = ref<Record<string, boolean>>({});

async function loadInitial() {
    loading.value = true;
    error.value = "";
    done.value = "";

    const res = await axios.get("/api/histories");
    histories.value = res.data.map((h: any) => ({ id: h.id, name: h.name }));

    if (histories.value.length > 0) {
        sourceHistoryId.value = histories.value[0]?.id || null;
        targetSingleId.value = histories.value[0]?.id || null;
        await loadSourceContents();
    }

    loading.value = false;
}

async function loadSourceContents() {
    if (!sourceHistoryId.value) {
        return;
    }

    error.value = "";
    done.value = "";

    const res = await axios.get(`/api/histories/${sourceHistoryId.value}/contents?types=dataset,dataset_collection`);
    const items = res.data;

    sourceContents.value = items.map((c: any) => ({
        id: c.id,
        name: c.name,
        hid: c.hid,
        type: c.history_content_type,
    }));

    sourceContentSelection.value = {};
    for (const item of sourceContents.value) {
        const key = `${item.type}|${item.id}`;
        sourceContentSelection.value[key] = false;
    }
}

function toggleAll(v: boolean) {
    for (const key in sourceContentSelection.value) {
        sourceContentSelection.value[key] = v;
    }
}

const selectedContentIds = computed(() => {
    const out: string[] = [];
    for (const key in sourceContentSelection.value) {
        if (sourceContentSelection.value[key]) {
            out.push(key);
        }
    }
    return out;
});

const resolvedTargetIds = computed(() => {
    const out: string[] = [];

    if (newHistoryName.value) {
        return out;
    }

    if (useMultipleTargets.value) {
        for (const id in targetMultiIds.value) {
            if (targetMultiIds.value[id]) {
                out.push(id);
            }
        }
        return out;
    }

    if (targetSingleId.value) {
        out.push(targetSingleId.value);
    }

    return out;
});

async function submitCopy() {
    loading.value = true;
    error.value = "";
    done.value = "";

    const body = {
        source_history: sourceHistoryId.value,
        source_content_ids: selectedContentIds.value,
        target_history_ids: newHistoryName.value ? null : resolvedTargetIds.value,
        target_history_name: newHistoryName.value || null,
    };

    try {
        const res = await axios.post("/api/datasets/copy", body);
        const historyIds = res.data.history_ids || [];
        const count = selectedContentIds.value.length;
        const targets = historyIds.length;
        done.value = `${count} item${count === 1 ? "" : "s"} copied to ${targets} histor${targets === 1 ? "y" : "ies"}.`;
        await loadSourceContents();
    } catch (e: any) {
        error.value = e?.response?.data?.err_msg || "Copy failed";
    }

    loading.value = false;
}

onMounted(loadInitial);
</script>

<template>
    <div class="p-4 space-y-4">
        <div v-if="error" class="text-red-600">{{ error }}</div>
        <div v-if="done" class="text-green-700">{{ done }}</div>

        <div class="text-gray-700">Copy history items</div>

        <div class="grid grid-cols-2 gap-6">
            <div>
                <div class="font-semibold mb-2">Source history</div>
                <select v-model="sourceHistoryId" class="border p-2 w-full" @change="loadSourceContents">
                    <option v-for="h in histories" :key="h.id" :value="h.id">{{ h.name }}</option>
                </select>

                <div class="mt-4">
                    <div class="flex space-x-2 mb-2">
                        <button type="button" class="px-2 py-1 border" @click="toggleAll(true)">All</button>
                        <button type="button" class="px-2 py-1 border" @click="toggleAll(false)">None</button>
                    </div>

                    <div v-if="sourceContents.length === 0" class="text-gray-500">This history has no datasets</div>

                    <div v-for="item in sourceContents" :key="item.id" class="flex space-x-2 mb-1">
                        <input
                            v-model="sourceContentSelection[`${item.type}|${item.id}`]"
                            type="checkbox"
                            :value="`${item.type}|${item.id}`" />
                        <span>{{ item.hid }}: {{ item.name }}</span>
                    </div>
                </div>
            </div>

            <div>
                <div class="font-semibold mb-2">Destination histories</div>

                <div v-if="!useMultipleTargets">
                    <label>Target</label>
                    <select v-model="targetSingleId" class="border p-2 w-full">
                        <option v-for="h in histories" :key="h.id" :value="h.id">{{ h.name }}</option>
                    </select>
                    <div class="text-blue-700 mt-2 cursor-pointer" @click="useMultipleTargets = true">
                        Choose multiple histories
                    </div>
                </div>

                <div v-else>
                    <div v-for="h in histories" :key="h.id" class="flex space-x-2 mb-1">
                        <input v-model="targetMultiIds[h.id]" type="checkbox" />
                        <span>{{ h.name }}</span>
                    </div>
                </div>

                <div class="mt-6 border-t pt-4">
                    <label>New history name</label>
                    <input v-model="newHistoryName" type="text" class="border p-2 w-full" />
                </div>

                <div class="mt-6 text-center">
                    <button type="button" class="px-4 py-2 border bg-gray-100" :disabled="loading" @click="submitCopy">
                        Copy items
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
