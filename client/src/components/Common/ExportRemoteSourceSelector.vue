<script setup lang="ts">
import { BFormGroup, BFormInput } from "bootstrap-vue";

import type { FilterFileSourcesOptions } from "@/api/remoteFiles";
import { useFileSources } from "@/composables/fileSources";
import localize from "@/utils/localization";

import FilesInput from "@/components/FilesDialog/FilesInput.vue";

interface Props {
    directory: string;
    fileName?: string;
    fileExtension?: string;
    resourceName?: string;
    filterOptions?: FilterFileSourcesOptions;
    showFileName?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    fileName: "",
    fileExtension: "",
    resourceName: "data",
    filterOptions: () => ({ exclude: ["rdm"] }),
    showFileName: false,
});

const emit = defineEmits<{
    (e: "update:directory", value: string): void;
    (e: "update:fileName", value: string): void;
}>();

const { hasWritable: hasWritableFileSources } = useFileSources(props.filterOptions);

const directoryDescription = localize(`Select a 'repository' to export ${props.resourceName} to.`);
const fileNameDescription = localize("Give the exported file a name.");
</script>

<template>
    <div>
        <p v-if="!hasWritableFileSources" class="text-warning">
            No writable file sources are configured. Please contact your administrator.
        </p>
        <template v-else>
            <BFormGroup id="fieldset-directory" label-for="directory" :description="directoryDescription" class="mt-3">
                <FilesInput
                    id="directory"
                    :value="props.directory"
                    mode="directory"
                    :require-writable="true"
                    :filter-options="props.filterOptions"
                    data-test-id="export-destination-input"
                    @input="emit('update:directory', $event)" />
            </BFormGroup>

            <BFormGroup
                v-if="props.showFileName"
                id="fieldset-name"
                label-for="name"
                :description="fileNameDescription"
                class="mt-3">
                <div class="d-flex align-items-center">
                    <BFormInput
                        id="name"
                        :value="props.fileName"
                        placeholder="Name"
                        required
                        data-test-id="export-file-name-input"
                        @input="emit('update:fileName', $event)" />
                    <span v-if="props.fileExtension" class="ml-2 text-muted">.{{ props.fileExtension }}</span>
                </div>
            </BFormGroup>
        </template>
    </div>
</template>
