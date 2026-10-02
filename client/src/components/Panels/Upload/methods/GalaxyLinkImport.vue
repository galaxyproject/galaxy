<script setup lang="ts">
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    method: { id: string };
    targetHistoryId: string;
}>();

const link = ref("");
const isImporting = ref(false);
const importedNames = ref<string[]>();
const errorMessage = ref<string>();
const trimmedLink = computed(() => link.value.trim());
const isWebLink = computed(() => /^https?:\/\//.test(trimmedLink.value));

const COULD_NOT_FETCH =
    "The link could not be imported. It may have expired, or the other Galaxy may not have finished preparing it.";

async function onImport() {
    isImporting.value = true;
    importedNames.value = undefined;
    errorMessage.value = undefined;
    try {
        const { data, error, response } = await GalaxyApi().POST("/api/histories/{history_id}/contents_from_store", {
            params: { path: { history_id: props.targetHistoryId } },
            body: { store_content_uri: trimmedLink.value, model_store_format: "tar.gz", discarded_data: "forbid" },
        });
        if (error) {
            // A link Galaxy could not fetch comes back as a bare 500 with no reason of its own.
            errorMessage.value = response.status >= 500 ? COULD_NOT_FETCH : errorMessageAsString(error);
            return;
        }
        importedNames.value = data.map((item) => item.name ?? "");
    } catch {
        errorMessage.value = COULD_NOT_FETCH;
    } finally {
        isImporting.value = false;
    }
}
</script>

<template>
    <div class="galaxy-link-import">
        <label for="galaxy-link-input">Link from another Galaxy</label>
        <input
            id="galaxy-link-input"
            v-model="link"
            class="form-control"
            data-description="galaxy link input"
            placeholder="https://usegalaxy.org/api/short_term_storage/..." />
        <GButton
            class="mt-2"
            data-description="galaxy link import"
            color="blue"
            :disabled="!isWebLink || isImporting"
            @click="onImport">
            Import
        </GButton>
        <p v-if="isImporting" class="mt-2">Importing...</p>
        <p v-else-if="importedNames" class="mt-2">Imported {{ importedNames.join(", ") }}.</p>
        <p v-else-if="errorMessage" class="mt-2 text-danger">{{ errorMessage }}</p>
    </div>
</template>
