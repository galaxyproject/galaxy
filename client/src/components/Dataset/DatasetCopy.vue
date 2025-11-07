<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";

const loading = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
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
    errorMessage.value = "";
    successMessage.value = "";

    const { data, error } = await GalaxyApi().GET("/api/histories");
    if (error) {
        errorMessage.value = error.err_msg;
    }
    if (Array.isArray(data)) {
        histories.value = data.map((h: any) => ({ id: h.id, name: h.name }));
        if (histories.value.length > 0) {
            sourceHistoryId.value = histories.value[0]?.id || null;
            targetSingleId.value = histories.value[0]?.id || null;
            await loadSourceContents();
        }
    }

    loading.value = false;
}

async function loadSourceContents() {
    if (sourceHistoryId.value) {
        errorMessage.value = "";
        successMessage.value = "";
        const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/contents", {
            params: {
                path: {
                    history_id: sourceHistoryId.value,
                },
            },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        }
        if (Array.isArray(data)) {
            sourceContents.value = data.map((c: any) => ({
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
    if (sourceHistoryId.value && selectedContentIds.value) {
        loading.value = true;
        errorMessage.value = "";
        successMessage.value = "";
        const { data: response, error } = await GalaxyApi().POST("/api/datasets/copy", {
            body: {
                source_history: sourceHistoryId.value,
                source_content_ids: selectedContentIds.value,
                target_history_ids: newHistoryName.value ? null : resolvedTargetIds.value,
                target_history_name: newHistoryName.value || null,
            },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        }
        if (response) {
            const historyIds = response.history_ids || [];
            const count = selectedContentIds.value.length;
            const targets = historyIds.length;
            successMessage.value = `${count} item${count === 1 ? "" : "s"} copied to ${targets} histor${targets === 1 ? "y" : "ies"}.`;
            await loadSourceContents();
        }
        loading.value = false;
    }
}

onMounted(loadInitial);
</script>

<template>
    <div class="p-4 space-y-4">
        <div v-if="errorMessage" class="text-red-600">{{ errorMessage }}</div>
        <div v-if="successMessage" class="text-green-700">{{ successMessage }}</div>

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
