<script setup lang="ts">
import { BAlert, BButton, BFormCheckbox, BFormInput, BFormSelect } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";

import Heading from "@/components/Common/Heading.vue";

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
            const [first] = histories.value as [{ id: string; name: string }];
            sourceHistoryId.value = first.id;
            targetSingleId.value = first.id;
            await loadSourceContents();
        }
    }
    loading.value = false;
}

async function loadSourceContents() {
    if (!sourceHistoryId.value) {
        return;
    }
    errorMessage.value = "";
    successMessage.value = "";
    const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/contents", {
        params: { path: { history_id: sourceHistoryId.value } },
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
            sourceContentSelection.value[`${item.type}|${item.id}`] = false;
        }
    }
}

function toggleAll(v: boolean) {
    for (const k in sourceContentSelection.value) {
        sourceContentSelection.value[k] = v;
    }
}

const selectedContent = computed(() => {
    const out: Array<{ id: string; type: string }> = [];
    for (const item of sourceContents.value) {
        const key = `${item.type}|${item.id}`;
        if (sourceContentSelection.value[key]) {
            out.push({ id: item.id, type: item.type });
        }
    }
    return out;
});

const resolvedTargetIds = computed(() => {
    if (newHistoryName.value) {
        return [];
    }
    if (useMultipleTargets.value) {
        return Object.keys(targetMultiIds.value).filter((k) => targetMultiIds.value[k]);
    }
    return targetSingleId.value ? [targetSingleId.value] : [];
});

async function submitCopy() {
    if (!sourceHistoryId.value || selectedContent.value.length === 0) {
        return;
    }
    loading.value = true;
    errorMessage.value = "";
    successMessage.value = "";
    const { data: response, error } = await GalaxyApi().POST("/api/datasets/copy", {
        body: {
            source_history: sourceHistoryId.value,
            source_content: selectedContent.value,
            target_history_ids: newHistoryName.value ? [] : resolvedTargetIds.value,
            target_history_name: newHistoryName.value || null,
        },
    });
    if (error) {
        errorMessage.value = error.err_msg;
    }
    if (response) {
        const targets = response.history_ids.length;
        const count = selectedContent.value.length;
        successMessage.value = `${count} item${count === 1 ? "" : "s"} copied to ${targets} histor${targets === 1 ? "y" : "ies"}.`;
        await loadSourceContents();
    }
    loading.value = false;
}

onMounted(loadInitial);
</script>

<template>
    <div>
        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <BAlert v-if="successMessage" variant="success" show>{{ successMessage }}</BAlert>
        <Heading h1 separator size="lg">Copy Datasets and Collections</Heading>
        <b-row>
            <b-col cols="6">
                <h6 class="mb-2">Source history</h6>
                <BFormSelect v-model="sourceHistoryId" class="mb-3" @change="loadSourceContents">
                    <option v-for="h in histories" :key="h.id" :value="h.id">
                        {{ h.name }}
                    </option>
                </BFormSelect>

                <div class="d-flex mb-2">
                    <BButton size="sm" variant="secondary" class="me-2" @click="toggleAll(true)">All</BButton>
                    <BButton size="sm" variant="secondary" @click="toggleAll(false)">None</BButton>
                </div>

                <div v-if="sourceContents.length === 0" class="text-muted">This history has no datasets</div>

                <div v-for="item in sourceContents" :key="item.id" class="d-flex align-items-center mb-1">
                    <BFormCheckbox v-model="sourceContentSelection[`${item.type}|${item.id}`]" class="me-2" />
                    <span>{{ item.hid }}: {{ item.name }}</span>
                </div>
            </b-col>

            <b-col cols="6">
                <h6 class="mb-2">Destination histories</h6>

                <div v-if="!useMultipleTargets">
                    <label class="form-label">Target</label>
                    <BFormSelect v-model="targetSingleId" class="mb-2">
                        <option v-for="h in histories" :key="h.id" :value="h.id">
                            {{ h.name }}
                        </option>
                    </BFormSelect>

                    <BButton variant="link" class="p-0" @click="useMultipleTargets = true">
                        Choose multiple histories
                    </BButton>
                </div>

                <div v-else>
                    <div v-for="h in histories" :key="h.id" class="d-flex align-items-center mb-1">
                        <BFormCheckbox v-model="targetMultiIds[h.id]" class="me-2" />
                        <span>{{ h.name }}</span>
                    </div>
                </div>

                <hr class="my-4" />

                <label class="form-label">New history name</label>
                <BFormInput v-model="newHistoryName" class="mb-3" />

                <div class="text-center">
                    <BButton variant="primary" :disabled="loading" @click="submitCopy"> Copy items </BButton>
                </div>
            </b-col>
        </b-row>
    </div>
</template>
