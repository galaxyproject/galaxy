<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBars, faCog, faDatabase, faSave, faTable, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BAlert, BButton, BSpinner, BTab, BTabs } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { updateContentFields } from "@/components/History/model/queries";
import { DatatypesProvider, DbKeyProvider, SuitableConvertersProvider } from "@/components/providers";
import { useConfig } from "@/composables/config";
import { useCollectionAttributesStore } from "@/stores/collectionAttributesStore";
import { useCollectionElementsStore } from "@/stores/collectionElementsStore";
import { useHistoryStore } from "@/stores/historyStore";
import localize from "@/utils/localization";
import { prependPath } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import ChangeDatatypeTab from "@/components/Collections/common/ChangeDatatypeTab.vue";
import DatabaseEditTab from "@/components/Collections/common/DatabaseEditTab.vue";
import SuitableConvertersTab from "@/components/Collections/common/SuitableConvertersTab.vue";
import Heading from "@/components/Common/Heading.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faBars, faCog, faDatabase, faSave, faTable, faUser);

interface Props {
    collectionId: string;
}

const props = defineProps<Props>();

const { config, isConfigLoaded } = useConfig(true);
const collectionAttributesStore = useCollectionAttributesStore();

const historyStore = useHistoryStore();
const { currentHistoryId } = storeToRefs(historyStore);

const collectionStore = useCollectionElementsStore();

const jobError = ref(null);
const errorMessage = ref("");
const infoMessage = ref("");
const successMessage = ref("");
const attributesInputs = ref<{ name: string; label: string; type: string; value: any }[]>([]);

/** 用于跟踪集合是否发生变化，并重新渲染 `FormDisplay` */
const collectionChangeKey = ref(0);

const attributesData = computed(() => {
    return collectionAttributesStore.getAttributes(props.collectionId);
});

const attributesLoadError = computed(() => {
    const itemLoadError = collectionAttributesStore.getItemLoadError(props.collectionId);
    if (itemLoadError) {
        return errorMessageAsString(itemLoadError);
    }
    return undefined;
});

const collection = computed(() => {
    return collectionStore.getCollectionById(props.collectionId);
});
const collectionLoadError = computed(() => {
    if (collection.value) {
        const collectionElementLoadError = collectionStore.getLoadingCollectionElementsError(collection.value);
        if (collectionElementLoadError) {
            return errorMessageAsString(collectionElementLoadError);
        }
    }
    return undefined;
});
watch([attributesLoadError, collectionLoadError], () => {
    if (attributesLoadError.value) {
        errorMessage.value = attributesLoadError.value;
    } else if (collectionLoadError.value) {
        errorMessage.value = collectionLoadError.value;
    }
});
const databaseKeyFromElements = computed(() => {
    return attributesData.value?.dbkey;
});
const datatypeFromElements = computed(() => {
    return attributesData.value?.extension;
});

watch(
    () => collection.value,
    (newVal) => {
        if (newVal) {
            collectionChangeKey.value++;
            attributesInputs.value = [
                {
                    name: "name",
                    label: "名称",
                    type: "text",
                    value: newVal.name,
                },
            ];
        }
    },
    { immediate: true }
);

function updateInfoMessage(strMessage: string) {
    infoMessage.value = strMessage;
    successMessage.value = "";
}

// TODO: 替换为实际的 datatype 类型
async function clickedSave(attribute: string, newValue: any) {
    if (attribute !== "dbkey") {
        // TODO: 扩展此功能以支持其他可以更改的属性
        console.error(`更改 ${attribute} 未实现`);
        return;
    }

    const dbKey = newValue.id as string;

    const { error } = await GalaxyApi().POST("/api/dataset_collections/{id}/copy", {
        params: { path: { id: props.collectionId } },
        body: { dbkey: dbKey },
    });
    if (error) {
        errorMessage.value = errorMessageAsString(error, `更改 ${attribute} 失败。`);
    }
}

// TODO: 替换为实际的 datatype 类型
async function clickedConvert(selectedConverter: any) {
    const url = prependPath(`/api/tools/${selectedConverter.tool_id}/convert`);
    const data = {
        src: "hdca",
        id: props.collectionId,
        source_type: selectedConverter.original_type,
        target_type: selectedConverter.target_type,
    };

    try {
        await axios.post(url, data).catch(handleError);
        successMessage.value = "转换成功开始。";
    } catch (err) {
        errorMessage.value = errorMessageAsString(err, "转换失败。");
    }
}

// TODO: 替换为实际的 datatype 类型
async function clickedDatatypeChange(selectedDatatype: any) {
    if (!currentHistoryId.value) {
        errorMessage.value = "没有选定当前历史记录。";
        return;
    }

    const { error } = await GalaxyApi().PUT("/api/histories/{history_id}/contents/bulk", {
        params: { path: { history_id: currentHistoryId.value } },
        body: {
            items: [
                {
                    history_content_type: "dataset_collection",
                    id: props.collectionId,
                },
            ],
            operation: "change_datatype",
            params: {
                type: "change_datatype",
                datatype: selectedDatatype.id,
            },
        },
    });

    if (error) {
        errorMessage.value = errorMessageAsString(error, "数据类型更改失败。");
        return;
    }
    successMessage.value = "数据类型更改成功。";
}

function handleError(err: any) {
    errorMessage.value = errorMessageAsString(err, "数据类型转换失败。");

    if (err?.data?.stderr) {
        jobError.value = err.data;
    }
}

function onAttribute(data: Record<string, any>) {
    for (const key in data) {
        const index = attributesInputs.value?.findIndex((input) => input.name === key);
        if (index !== -1 && attributesInputs.value[index]) {
            attributesInputs.value[index]!.value = data[key];
        }
    }
}

async function saveAttrs() {
    if (collection.value && attributesInputs.value) {
        const updatedAttrs = attributesInputs.value.reduce((acc, input) => {
            acc[input.name] = input.value;
            return acc;
        }, {} as Record<string, any>);
        try {
            await updateContentFields(collection.value, updatedAttrs);

            successMessage.value = "属性更新成功。";
        } catch (err) {
            errorMessage.value = errorMessageAsString(err, "无法更新属性。");
        }
    }
}
</script>

<template>
    <div aria-labelledby="collection-edit-view-heading">
        <Heading id="dataset-attributes-heading" h1 separator inline size="xl">
            {{ localize("编辑集合属性") }}
        </Heading>

        <BAlert v-if="infoMessage" show variant="info" dismissible>
            {{ localize(infoMessage) }}
        </BAlert>

        <BAlert v-if="errorMessage" show variant="danger">
            {{ localize(errorMessage) }}
        </BAlert>

        <BAlert v-if="successMessage" show variant="success" dismissible>
            {{ localize(successMessage) }}
        </BAlert>
        <BTabs v-if="!errorMessage" class="mt-3">
            <BTab title-link-class="collection-edit-attributes-nav" @click="updateInfoMessage('')">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faBars" class="mr-1" />
                    {{ localize("属性") }}
                </template>

                <FormDisplay
                    v-if="attributesInputs.length > 0"
                    :key="collectionChangeKey"
                    :inputs="attributesInputs"
                    @onChange="onAttribute" />

                <div class="mt-2">
                    <BButton id="dataset-attributes-default-save" variant="primary" @click="saveAttrs">
                        <FontAwesomeIcon :icon="faSave" class="mr-1" />
                        {{ localize("保存") }}
                    </BButton>
                </div>
            </BTab>
            <BTab
                title-link-class="collection-edit-change-genome-nav"
                @click="
                    updateInfoMessage(
                        '这将创建一个新的集合到您的历史记录。您的配额不会增加。'
                    )
                ">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faTable" class="mr-1" />
                    {{ localize("数据库/构建") }}
                </template>

                <DbKeyProvider v-slot="{ item, loading }">
                    <div v-if="loading">
                        <BSpinner label="加载数据库/构建..." />
                    </div>
                    <div v-else>
                        <DatabaseEditTab
                            v-if="item && databaseKeyFromElements"
                            :database-key-from-elements="databaseKeyFromElements"
                            :genomes="item"
                            @clicked-save="clickedSave" />
                    </div>
                </DbKeyProvider>
            </BTab>

            <SuitableConvertersProvider :id="collectionId" v-slot="{ item }">
                <BTab
                    v-if="item && item.length"
                    title-link-class="collection-edit-convert-datatype-nav"
                    @click="updateInfoMessage('这将创建一个新的集合到您的历史记录。')">
                    <template v-slot:title>
                        <FontAwesomeIcon :icon="faCog" class="mr-1" />
                        {{ localize("转换") }}
                    </template>

                    <SuitableConvertersTab :suitable-converters="item" @clicked-convert="clickedConvert" />
                </BTab>
            </SuitableConvertersProvider>

            <BTab
                v-if="isConfigLoaded && config.enable_celery_tasks"
                title-link-class="collection-edit-change-datatype-nav"
                @click="
                    updateInfoMessage(
                        '此操作可能需要一段时间，具体取决于您的集合大小。'
                    )
                ">
                <template v-slot:title>
                    <FontAwesomeIcon :icon="faDatabase" class="mr-1" />
                    {{ localize("数据类型") }}
                </template>

                <DatatypesProvider v-slot="{ item, loading }">
                    <div v-if="loading">
                        <LoadingSpan message="加载数据类型" />
                    </div>
                    <div v-else>
                        <ChangeDatatypeTab
                            v-if="item && datatypeFromElements"
                            :datatype-from-elements="datatypeFromElements"
                            :datatypes="item"
                            @clicked-save="clickedDatatypeChange" />
                    </div>
                </DatatypesProvider>
            </BTab>
        </BTabs>
    </div>
</template>
