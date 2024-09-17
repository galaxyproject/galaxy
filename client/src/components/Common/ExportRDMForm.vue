<script setup lang="ts">
import { BButton, BCard, BFormGroup, BFormInput, BFormRadio, BFormRadioGroup } from "bootstrap-vue";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { type BrowsableFilesSourcePlugin, type CreatedEntry, type FilterFileSourcesOptions } from "@/api/remoteFiles";
import { useToast } from "@/composables/toast";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { fileSourcePluginToItem } from "../FilesDialog/utilities";

import ExternalLink from "@/components/ExternalLink.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";

const toast = useToast();

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

type ExportChoice = "existing" | "new";

const includeOnlyRDMCompatible: FilterFileSourcesOptions = { include: ["rdm"] };

const recordUri = ref<string>("");
const sourceUri = ref<string>(props.fileSource?.uri_root ?? "");
const fileName = ref<string>(props.defaultFilename);
const exportChoice = ref<ExportChoice>("new");
const recordName = ref<string>(props.defaultRecordName);
const newEntry = ref<CreatedEntry>();

const canCreateRecord = computed(() => Boolean(sourceUri.value) && Boolean(recordName.value));

const canExport = computed(() => Boolean(recordUri.value) && Boolean(fileName.value));

const repositoryRecordDescription = computed(() => localize(`Select a repository to export ${props.what} to.`));

const nameDescription = computed(() => localize("Give the exported file a name."));
const recordNameDescription = computed(() => localize("Give the new record a name or title."));

const namePlaceholder = computed(() => localize("File name"));
const recordNamePlaceholder = computed(() => localize("Record name"));

const uniqueSourceId = computed(() => props.fileSource?.id ?? "any");
const fileSourceAsItem = computed(() => (props.fileSource ? fileSourcePluginToItem(props.fileSource) : undefined));

function doExport() {
    emit("export", recordUri.value, fileName.value);

    if (props.clearInputAfterExport) {
        clearInputs();
    }
}

async function doCreateRecord() {
    const { data, error } = await GalaxyApi().POST("/api/remote_files", {
        body: {
            target: sourceUri.value,
            name: recordName.value,
        },
    });

    if (error) {
        toast.error(errorMessageAsString(error));
        return;
    }

    newEntry.value = data;
    recordUri.value = newEntry.value.uri;
}

function clearInputs() {
    recordUri.value = "";
    sourceUri.value = props.fileSource?.uri_root ?? "";
    fileName.value = "";
    newEntry.value = undefined;
}
</script>

<template>
    <div class="export-to-rdm-repository">
        <BFormGroup id="fieldset-name" label-for="name" :description="nameDescription" class="mt-3">
            <BFormInput id="file-name-input" v-model="fileName" :placeholder="namePlaceholder" required />
        </BFormGroup>

        <p>
            Your {{ what }} needs to be uploaded to an existing <i>draft</i> record. You will need to create a
            <b>new record</b> or select an existing <b>draft record</b> and then export your {{ what }} to it.
        </p>

        <BFormRadioGroup v-model="exportChoice" class="export-radio-group">
            <BFormRadio :id="`radio-new-${uniqueSourceId}`" v-localize name="exportChoice" value="new">
                Export to new record
            </BFormRadio>

            <BFormRadio :id="`radio-existing-${uniqueSourceId}`" v-localize name="exportChoice" value="existing">
                Export to existing draft record
            </BFormRadio>
        </BFormRadioGroup>

        <div v-if="exportChoice === 'new'">
            <div v-if="newEntry">
                <BCard>
                    <p>
                        <b>{{ newEntry.name }}</b>
                        <span v-localize> draft record has been created in the repository.</span>
                    </p>

                    <p v-if="newEntry.external_link">
                        You can preview the record in the repository, further edit its metadata and decide when to
                        publish it at
                        <ExternalLink :href="newEntry.external_link">
                            <b>{{ newEntry.external_link }}</b>
                        </ExternalLink>
                    </p>

                    <p v-localize>Please use the button below to upload the exported {{ props.what }} to the record.</p>

                    <BButton
                        id="export-button-new-record"
                        v-localize
                        class="export-button"
                        variant="primary"
                        :disabled="!canExport"
                        @click.prevent="doExport">
                        Export to this record
                    </BButton>
                </BCard>
            </div>
            <div v-else>
                <BFormGroup
                    v-if="!props.fileSource"
                    id="fieldset-record-new"
                    label-for="source-selector"
                    :description="repositoryRecordDescription"
                    class="mt-3">
                    <FilesInput
                        id="source-selector"
                        v-model="sourceUri"
                        mode="source"
                        :require-writable="true"
                        :filter-options="includeOnlyRDMCompatible" />
                </BFormGroup>

                <BFormGroup
                    id="fieldset-record-name"
                    label-for="record-name"
                    :description="recordNameDescription"
                    class="mt-3">
                    <BFormInput
                        id="record-name-input"
                        v-model="recordName"
                        :placeholder="recordNamePlaceholder"
                        required />
                </BFormGroup>

                <p v-localize>
                    You need to create the new record in a repository before exporting the {{ props.what }} to it.
                </p>

                <BButton
                    id="create-record-button"
                    v-localize
                    variant="primary"
                    :disabled="!canCreateRecord"
                    @click.prevent="doCreateRecord">
                    Create new record
                </BButton>
            </div>
        </div>
        <div v-else>
            <BFormGroup
                id="fieldset-record-existing"
                label-for="existing-record-selector"
                :description="repositoryRecordDescription"
                class="mt-3">
                <FilesInput
                    id="existing-record-selector"
                    v-model="recordUri"
                    mode="directory"
                    :require-writable="true"
                    :filter-options="fileSource ? undefined : includeOnlyRDMCompatible"
                    :selected-item="fileSourceAsItem" />
            </BFormGroup>

            <BButton
                id="export-button-existing-record"
                v-localize
                class="export-button"
                variant="primary"
                :disabled="!canExport"
                @click.prevent="doExport">
                Export to existing record
            </BButton>
        </div>
    </div>
</template>
