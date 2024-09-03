<script setup lang="ts">
import { BButton, BCol, BFormGroup, BFormInput, BRow } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type FilterFileSourcesOptions } from "@/api/remoteFiles";
import localize from "@/utils/localization";

import FilesInput from "@/components/FilesDialog/FilesInput.vue";

interface Props {
    what?: string;
    clearInputAfterExport?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    what: "archive",
    clearInputAfterExport: false,
});

const emit = defineEmits<{
    (e: "export", directory: string, name: string): void;
}>();

const defaultExportFilterOptions: FilterFileSourcesOptions = { exclude: ["rdm"] };

const directory = ref<string>("");
const name = ref<string>("");

const canExport = computed(() => name.value.length > 0 && directory.value.length > 0);

const directoryDescription = computed(() => localize(`Select a 'remote files' directory to export ${props.what} to.`));

const nameDescription = computed(() => localize("Give the exported file a name."));

const namePlaceholder = computed(() => localize("Name"));

const doExport = () => {
    emit("export", directory.value, name.value);
    if (props.clearInputAfterExport) {
        directory.value = "";
        name.value = "";
    }
};
</script>

<template>
    <div class="export-to-remote-file">
        <BFormGroup id="fieldset-directory" label-for="directory" :description="directoryDescription" class="mt-3">
            <FilesInput
                id="directory"
                v-model="directory"
                mode="directory"
                :require-writable="true"
                :filter-options="defaultExportFilterOptions" />
        </BFormGroup>

        <BFormGroup id="fieldset-name" label-for="name" :description="nameDescription" class="mt-3">
            <BFormInput id="name" v-model="name" :placeholder="namePlaceholder" required />
        </BFormGroup>

        <BRow align-h="end">
            <BCol>
                <BButton
                    v-localize
                    class="export-button"
                    variant="primary"
                    :disabled="!canExport"
                    @click.prevent="doExport">
                    Export
                </BButton>
            </BCol>
        </BRow>
    </div>
</template>
