<script setup lang="ts">
import { BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, onUnmounted, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { useTaskMonitor } from "@/composables/taskMonitor";
import { errorMessageAsString } from "@/utils/simple-error";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    method: { id: string };
    targetHistoryId: string;
}>();

const COULD_NOT_IMPORT =
    "The link could not be imported. It may have expired, or the other Galaxy may not have finished preparing it.";

const { waitForTask, stopWaitingForTask, isRunning, isCompleted, hasFailed, failureReason, requestHasFailed } =
    useTaskMonitor();

const link = ref("");
const isStarting = ref(false);
const startError = ref<string>();
const trimmedLink = computed(() => link.value.trim());
const isWebLink = computed(() => /^https?:\/\//.test(trimmedLink.value));
const isImporting = computed(() => isStarting.value || isRunning.value);

// Clearing the link keeps a second click from importing the same items again.
watch(isCompleted, (completed) => {
    if (completed) {
        link.value = "";
    }
});

async function onImport() {
    isStarting.value = true;
    startError.value = undefined;
    try {
        const { data, error } = await GalaxyApi().POST("/api/histories/{history_id}/contents_from_store_async", {
            params: { path: { history_id: props.targetHistoryId } },
            body: { store_content_uri: trimmedLink.value, model_store_format: "tar.gz", discarded_data: "forbid" },
        });
        if (error) {
            startError.value = errorMessageAsString(error);
            return;
        }
        waitForTask(data.id, 3000);
    } catch (e) {
        startError.value = errorMessageAsString(e, COULD_NOT_IMPORT);
    } finally {
        isStarting.value = false;
    }
}

onUnmounted(stopWaitingForTask);
</script>

<template>
    <div class="galaxy-link-import">
        <BFormGroup
            label="Link from another Galaxy"
            label-for="galaxy-link-input"
            description="Made with Export to another Galaxy on the other server.">
            <BFormInput
                id="galaxy-link-input"
                v-model="link"
                type="url"
                data-description="galaxy link input"
                placeholder="https://usegalaxy.org/api/short_term_storage/..."
                :disabled="isImporting" />
        </BFormGroup>
        <GButton
            color="blue"
            data-description="galaxy link import"
            :disabled="!isWebLink || isImporting"
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
            Galaxy could not check how the import is going. It may still finish, so look at the history before trying
            again.
        </GAlert>
        <GAlert v-else-if="isCompleted" variant="success" class="mt-3" show>
            Done! The items were imported into
            <SwitchToHistoryLink :history-id="props.targetHistoryId" :inline="true" :thin="false" />
        </GAlert>
    </div>
</template>
