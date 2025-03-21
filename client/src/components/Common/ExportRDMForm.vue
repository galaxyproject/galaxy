<script setup lang="ts">
import { BButton, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type BrowsableFilesSourcePlugin } from "@/api/remoteFiles";
import localize from "@/utils/localization";

import RDMDestinationSelector from "@/components/Common/RDMDestinationSelector.vue";

interface Props {
    what?: string;
    clearInputAfterExport?: boolean;
    defaultRecordName?: string;
    defaultFilename?: string;
    /**
     * If undefined, the user will need to select a repository to export to,
     * otherwise this file source will be pre-selected.
     */
    fileSource?: BrowsableFilesSourcePlugin;
}

const props = withDefaults(defineProps<Props>(), {
    what: "archive",
    clearInputAfterExport: false,
    defaultRecordName: "",
    defaultFilename: "",
    fileSource: undefined,
});

const emit = defineEmits<{
    (e: "export", recordUri: string, fileName: string, newRecordName?: string): void;
}>();

const destinationSelector = ref<InstanceType<typeof RDMDestinationSelector>>();

const recordUri = ref<string>("");
const fileName = ref<string>(props.defaultFilename);
const isNewRecord = ref(true);

const canExport = computed(() => Boolean(recordUri.value) && Boolean(fileName.value));

const nameDescription = computed(() => localize("为导出的文件命名。"));

const namePlaceholder = computed(() => localize("文件名"));

function doExport() {
    emit("export", recordUri.value, fileName.value);

    if (props.clearInputAfterExport) {
        clearInputs();
    }
}

function clearInputs() {
    recordUri.value = "";
    fileName.value = "";

    //@ts-ignore incorrect property not found error
    destinationSelector.value?.reset();
}

function onRecordSelected(selectedRecordUri: string) {
    recordUri.value = selectedRecordUri;
}
</script>

<template>
    <div class="export-to-rdm-repository">
        <BFormGroup id="fieldset-name" label-for="name" :description="nameDescription" class="mt-3">
            <BFormInput id="file-name-input" v-model="fileName" :placeholder="namePlaceholder" required />
        </BFormGroup>

        <RDMDestinationSelector
            ref="destinationSelector"
            :what="what"
            :file-source="fileSource"
            @onRecordSelected="onRecordSelected" />

        <div v-if="isNewRecord">
            <p v-localize class="mt-3">
                请使用下面的按钮将导出的 {{ props.what }} 上传到该记录。
            </p>

            <BButton
                id="export-button-new-record"
                v-localize
                class="export-button"
                variant="primary"
                :disabled="!canExport"
                @click.prevent="doExport">
                导出到此记录
            </BButton>
        </div>
        <div v-else>
            <BButton
                id="export-button-existing-record"
                v-localize
                class="export-button"
                variant="primary"
                :disabled="!canExport"
                @click.prevent="doExport">
                导出到现有记录
            </BButton>
        </div>
    </div>
</template>
