<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { sortTrsVersions, trsVersionId } from "@/components/Workflow/Import/trsVersion";
import type { TrsSelection, TrsTool, TrsVersionReference } from "@/components/Workflow/Import/types";
import { Services } from "@/components/Workflow/services";
import { errorMessageAsString } from "@/utils/simple-error";

import GSelect from "@/components/BaseComponents/GSelect.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";

const emit = defineEmits<{
    (e: "target", target: TrsVersionReference | null): void;
}>();

const services = new Services();

const servers = ref<TrsSelection[]>([]);
const serverId = ref<string | null>(null);
const toolId = ref("");
const tool = ref<TrsTool | null>(null);
const selectedVersion = ref<string | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const versionOptions = computed(() =>
    sortTrsVersions(tool.value?.versions ?? []).map((version) => ({
        value: trsVersionId(version),
        text: version.name,
    })),
);

const target = computed<TrsVersionReference | null>(() =>
    serverId.value && tool.value && selectedVersion.value
        ? { trs_server: serverId.value, trs_tool_id: tool.value.id, trs_version_id: selectedVersion.value }
        : null,
);

watch(target, (newTarget) => emit("target", newTarget));

async function loadServers() {
    try {
        servers.value = await services.getTrsServers();
        serverId.value = servers.value[0]?.id ?? null;
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
}

loadServers();

let loadCount = 0;

watch([serverId, toolId], async ([server, id]) => {
    const current = ++loadCount;
    const trimmedId = id.trim();
    tool.value = null;
    selectedVersion.value = null;
    error.value = null;
    loading.value = Boolean(server && trimmedId);
    if (!server || !trimmedId) {
        return;
    }
    try {
        const loaded = await services.getTrsTool(server, trimmedId);
        if (current === loadCount) {
            tool.value = loaded;
            selectedVersion.value = versionOptions.value[0]?.value ?? null;
        }
    } catch (e) {
        if (current === loadCount) {
            error.value = errorMessageAsString(e);
        }
    } finally {
        if (current === loadCount) {
            loading.value = false;
        }
    }
});
</script>

<template>
    <div>
        <GSelect v-if="servers.length > 1" v-model="serverId" size="small" class="mt-1" aria-label="TRS server">
            <option v-for="server in servers" :key="server.id" :value="server.id">{{ server.label }}</option>
        </GSelect>
        <DelayedInput
            v-model="toolId"
            class="mt-1"
            placeholder="TRS id, e.g. #workflow/github.com/org/repo/main"
            :delay="800"
            :loading="loading" />
        <div v-if="error" class="text-danger">{{ error }}</div>
        <GSelect
            v-if="versionOptions.length"
            v-model="selectedVersion"
            size="small"
            class="mt-1"
            aria-label="TRS version of the replacement workflow">
            <option v-for="option in versionOptions" :key="option.value" :value="option.value">
                {{ option.text }}
            </option>
        </GSelect>
    </div>
</template>
