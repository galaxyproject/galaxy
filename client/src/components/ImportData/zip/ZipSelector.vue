<script setup lang="ts">
import { faLaptop } from "@fortawesome/free-solid-svg-icons";
import { ref, watch } from "vue";

import { isZipFile, useZipExplorer } from "@/composables/zipExplorer";

import GCard from "@/components/Common/GCard.vue";

const { errorMessage, isValidUrl } = useZipExplorer();

const fileInputRef = ref<HTMLInputElement>();
const zipUrl = ref<string>();

const emit = defineEmits<{
    (e: "zipSourceChanged", source?: File | string): void;
}>();

function browseZipFile() {
    fileInputRef.value?.click();
}

async function onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;

    errorMessage.value = isZipFile(file);
    if (!errorMessage.value && file) {
        emit("zipSourceChanged", file);
    }
}

function onUrlChange() {
    if (!isValidUrl(zipUrl.value)) {
        errorMessage.value = "Invalid URL provided.";
        return;
    }
    emit("zipSourceChanged", zipUrl.value);
}

watch(
    () => zipUrl.value,
    (val) => {
        if (val === "" || val === undefined) {
            errorMessage.value = undefined;
        }
    }
);

const primaryActions = [
    {
        id: "btn-local",
        title: "",
        label: "Browse local ZIP",
        icon: faLaptop,
        handler: browseZipFile,
        visible: true,
    },
];
</script>

<template>
    <div class="w-100">
        <div class="d-flex flex-grow-1">
            <GCard
                id="zip-file-local"
                :primary-actions="primaryActions"
                class="wizard-selection-card"
                title="Option A: Select Local ZIP file"
                description="Click on the `Browse local ZIP` button to select a ZIP file from your computer. Then you can preview and select files to import from it. This is useful when you are only interested in a few files from a large ZIP file." />

            <label style="display: none">
                <input ref="fileInputRef" type="file" accept=".zip" @change="onFileChange" />
            </label>

            <GCard id="zip-file-remote" class="wizard-selection-card" title="Option B: Select Remote ZIP file">
                <template v-slot:description>
                    <p v-localize>Enter the URL of a ZIP file.</p>
                    <label v-localize class="w-100" for="rocrate-zip-url">
                        <input id="rocrate-zip-url" v-model="zipUrl" type="text" class="w-100" @change="onUrlChange" />
                    </label>
                    <strong>Note:</strong> The URL must be publicly accessible and should point to a ZIP file.
                    <div v-if="errorMessage" v-localize class="text-danger">{{ errorMessage }}</div>
                </template>
            </GCard>
        </div>
    </div>
</template>
