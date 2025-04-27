<script setup lang="ts">
import { faLaptop } from "@fortawesome/free-solid-svg-icons";
import { computed, ref, watch } from "vue";

import { isZipFile, useZipExplorer } from "@/composables/zipExplorer";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";

const { isValidUrl, reset: resetExplorer } = useZipExplorer();

const props = defineProps<{
    zipSource?: File | string;
}>();

const fileInputRef = ref<HTMLInputElement>();

const zipUrl = ref<string>(typeof props.zipSource === "string" ? props.zipSource : "");

const zipFile = ref<File | null>(props.zipSource instanceof File ? props.zipSource : null);

const errorMessage = ref<string>();

const zipFilePath = computed(() => {
    if (zipFile.value) {
        return zipFile.value.name;
    }
    return "";
});

const isSourceSelected = computed(() => {
    return zipFile.value !== null || Boolean(zipUrl.value);
});

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
        zipFile.value = file;
        zipUrl.value = "";
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

function reset() {
    resetExplorer();
    zipFile.value = null;
    zipUrl.value = "";
    errorMessage.value = undefined;
    emit("zipSourceChanged", undefined);
}

watch(
    () => zipUrl.value,
    (newVal, oldVal) => {
        if (newVal === "" || newVal === undefined) {
            errorMessage.value = undefined;
        } else if (newVal !== oldVal) {
            onUrlChange();
        }
    }
);

const localFileActions = [
    {
        id: "btn-local",
        title: "Select a compressed archive from your computer",
        label: "Browse local archive",
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
                :primary-actions="localFileActions"
                class="wizard-selection-card"
                title="🖥️ Option A: Select local archive">
                <template v-slot:description>
                    <p v-localize>
                        Click on the `Browse local archive` button to select a compressed archive file from your
                        computer (<b>only ZIP files are supported</b> for now). Then you can preview and select files to
                        import from it. This is
                        <b>useful when you are only interested in a few small files from a large compressed archive</b>.
                    </p>
                    <label class="w-100" for="zip-file-path">
                        <input id="zip-file-path" v-model="zipFilePath" type="text" class="w-100" readonly />
                    </label>
                </template>
            </GCard>

            <label style="display: none">
                <input ref="fileInputRef" type="file" accept=".zip" @change="onFileChange" />
            </label>

            <GCard id="zip-file-remote" class="wizard-selection-card" title="🌐 Option B: Select remote archive">
                <template v-slot:description>
                    <p v-localize>
                        Enter or paste the URL of a ZIP file. You will be able to preview and select files to import
                        from it without downloading the entire archive.
                    </p>
                    <label class="w-100" for="zip-url">
                        <input id="zip-url" v-model="zipUrl" type="text" class="w-100" />
                    </label>
                    <strong>Note:</strong> The URL must be
                    <strong>publicly accessible and should point to a ZIP file</strong>. In addition,
                    <strong>the remote host must support byte-range requests</strong>. This is required to allow the
                    preview and access to the ZIP file contents without downloading the entire archive.
                    <div v-if="errorMessage" v-localize class="text-danger">{{ errorMessage }}</div>
                </template>
            </GCard>
        </div>

        <GButton
            id="btn-clear-zip-selection"
            class="mt-2"
            :secondary="true"
            :disabled="!isSourceSelected"
            @click="reset">
            Clear selection
        </GButton>
    </div>
</template>
