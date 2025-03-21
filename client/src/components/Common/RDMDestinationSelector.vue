<script setup lang="ts">
import { BAlert, BButton, BCard, BFormGroup, BFormInput, BFormRadio, BFormRadioGroup } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { type BrowsableFilesSourcePlugin, type CreatedEntry, type FilterFileSourcesOptions } from "@/api/remoteFiles";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { fileSourcePluginToItem } from "../FilesDialog/utilities";

import ExternalLink from "@/components/ExternalLink.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";

type ExportChoice = "existing" | "new";

interface Props {
    what?: string;
    /**
     * If undefined, the user will need to select a repository to export to,
     * otherwise this file source will be pre-selected.
     */
    fileSource?: BrowsableFilesSourcePlugin;
}

const props = withDefaults(defineProps<Props>(), {
    what: "archive",
    fileSource: undefined,
});

const emit = defineEmits<{
    (e: "onRecordSelected", recordUri: string): void;
}>();

const includeOnlyRDMCompatible: FilterFileSourcesOptions = { include: ["rdm"] };

const recordUri = ref<string>("");
const sourceUri = ref<string>(props.fileSource?.uri_root ?? "");
const exportChoice = ref<ExportChoice>("new");
const recordName = ref<string>("");
const newEntry = ref<CreatedEntry>();

const canCreateRecord = computed(() => Boolean(sourceUri.value) && Boolean(recordName.value));

const errorCreatingRecord = ref<string>();

const repositoryRecordDescription = computed(() => localize(`选择一个存储库以导出 ${props.what} 到那里。`));

const recordNameDescription = computed(() => localize("为新记录指定一个名称或标题。"));

const recordNamePlaceholder = computed(() => localize("记录名称"));

const uniqueSourceId = computed(() => props.fileSource?.id ?? "任何");
const fileSourceAsItem = computed(() => (props.fileSource ? fileSourcePluginToItem(props.fileSource) : undefined));

watch(
    () => recordUri.value,
    (value) => {
        emit("onRecordSelected", value);
    }
);

async function onCreateRecord() {
    try {
        await createRecord();
    } catch (error) {
        errorCreatingRecord.value = errorMessageAsString(error);
    }
}

async function createRecord() {
    const { data, error } = await GalaxyApi().POST("/api/remote_files", {
        body: {
            target: sourceUri.value,
            name: recordName.value,
        },
    });

    if (error) {
        errorCreatingRecord.value = errorMessageAsString(error);
        return;
    }

    newEntry.value = data;
    recordUri.value = newEntry.value.uri;
}

function reset() {
    recordUri.value = "";
    recordName.value = "";
    newEntry.value = undefined;
    exportChoice.value = "new";
}

defineExpose({
    reset,
});
</script>

<template>
    <div>
        <p>
            您的 {{ what }} 需要上传到现有的 <i>草稿</i> 记录中。您需要创建一个
            <b>新记录</b> 或选择一个现有的 <b>草稿记录</b>，然后将您的 {{ what }} 导出到其中。
        </p>

        <BFormRadioGroup v-model="exportChoice" class="export-radio-group">
            <BFormRadio :id="`radio-new-${uniqueSourceId}`" v-localize name="exportChoice" value="new">
                导出到新记录
            </BFormRadio>

            <BFormRadio :id="`radio-existing-${uniqueSourceId}`" v-localize name="exportChoice" value="existing">
                导出到现有的草稿记录
            </BFormRadio>
        </BFormRadioGroup>

        <div v-if="exportChoice === 'new'">
            <div v-if="newEntry">
                <BCard>
                    <p>
                        <b>{{ newEntry.name }}</b>
                        <span v-localize> 草稿记录已经在存储库中创建。</span>
                    </p>

                    <div v-if="newEntry.external_link">
                        您可以在存储库中预览记录，进一步编辑其元数据并决定何时发布，链接地址为
                        <ExternalLink :href="newEntry.external_link">
                            <b>{{ newEntry.external_link }}</b>
                        </ExternalLink>
                    </div>
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
                    您需要在存储库中创建新记录，然后才能将 {{ props.what }} 导出到其中。
                </p>

                <BAlert
                    v-if="errorCreatingRecord"
                    variant="danger"
                    show
                    dismissible
                    @dismissed="errorCreatingRecord = undefined">
                    创建记录时发生错误：
                    {{ errorCreatingRecord }}
                </BAlert>

                <BButton
                    id="create-record-button"
                    v-localize
                    variant="primary"
                    :disabled="!canCreateRecord"
                    @click.prevent="onCreateRecord">
                    创建新记录
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
        </div>
    </div>
</template>