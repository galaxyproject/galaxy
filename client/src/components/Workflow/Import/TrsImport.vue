<script setup lang="ts">
import { BAlert, BCard, BFormGroup, BFormInput } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, type Ref, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { Services } from "@/components/Workflow/services";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import type { TrsSelection, TrsTool as TrsToolInterface } from "./types";

import LoadingSpan from "@/components/LoadingSpan.vue";
import TrsServerSelection from "@/components/Workflow/Import/TrsServerSelection.vue";
import TrsTool from "@/components/Workflow/Import/TrsTool.vue";
import TrsUrlImport from "@/components/Workflow/Import/TrsUrlImport.vue";

interface Props {
    isRun?: boolean;
    queryTrsId?: string;
    queryTrsUrl?: string;
    queryTrsServer?: string;
    queryTrsVersionId?: string;
}

const props = defineProps<Props>();

const trsTool: Ref<TrsToolInterface | null> = ref(null);
const loading = ref(false);
const importing = ref(false);
const trsSelection: Ref<TrsSelection | null> = ref(null);
const errorMessage: Ref<string | null> = ref(null);
const toolId = ref(props.queryTrsId);
const { isAnonymous } = storeToRefs(useUserStore());
const isAutoImport = ref(
    Boolean((props.queryTrsVersionId && props.queryTrsServer && props.queryTrsId) || props.queryTrsUrl)
);

const toolIdTrimmed = computed(() => {
    return toolId.value?.trim() || null;
});

const hasErrorMessage = computed(() => {
    return errorMessage.value != null;
});

watch(toolIdTrimmed, () => {
    onToolId();
});

const services = new Services();

async function onToolId() {
    trsTool.value = null;
    errorMessage.value = null;

    if (!trsSelection.value || !toolIdTrimmed.value) {
        return;
    }

    loading.value = true;

    try {
        const tool = await services.getTrsTool(trsSelection.value.id, toolIdTrimmed.value);

        trsTool.value = tool;

        if (isAutoImport.value) {
            let versionField: "name" | "id" = "name";
            const version = trsTool.value!.versions.find((version) => {
                if (version.name === props.queryTrsVersionId) {
                    return true;
                } else if (version.id === props.queryTrsVersionId) {
                    versionField = "id";
                    return true;
                }
            });

            if (version) {
                importVersion(trsSelection.value.id, trsTool.value!.id, version[versionField], props.isRun);
            } else {
                Toast.warning(`指定的版本: ${props.queryTrsVersionId} 不存在`);
                isAutoImport.value = false;
            }
        }
    } catch (error) {
        trsTool.value = null;
        errorMessage.value = error as string;
    } finally {
        loading.value = false;
    }
}

function onTrsSelection(selection: TrsSelection) {
    trsSelection.value = selection;

    if (toolIdTrimmed.value) {
        onToolId();
    }
}

function onTrsSelectionError(message: string) {
    errorMessage.value = message;
}

const router = useRouter();

async function importVersion(trsId?: string, toolIdToImport?: string, version?: string, isRunFormRedirect = false) {
    if (!trsId || !toolIdToImport) {
        errorMessage.value = "导入失败。未知ID";
        return;
    }

    importing.value = true;
    errorMessage.value = null;

    try {
        const response = await services.importTrsTool(trsId, toolIdToImport, version);
        const path = getRedirectOnImportPath(response, isRunFormRedirect);

        router.push(path);
    } catch (error) {
        errorMessage.value = (error as string) || "导入因未知原因失败。";
    } finally {
        importing.value = false;
    }
}

async function importVersionFromUrl(url: string, isRunFormRedirect = false) {
    importing.value = true;
    errorMessage.value = null;

    try {
        const response = await services.importTrsToolFromUrl(url);
        const path = getRedirectOnImportPath(response, isRunFormRedirect);

        router.push(path);
    } catch (error) {
        errorMessage.value = (error as string) || "导入因未知原因失败。";
    } finally {
        importing.value = false;
    }
}
</script>

<template>
    <div class="workflow-import-trs-id">
        <BCard v-if="!isAnonymous" title="GA4GH 工具注册服务器 (TRS) 工作流导入">
            <div>
                <b>TRS 服务器:</b>

                <TrsServerSelection
                    :trs-selection="trsSelection"
                    :query-trs-server="props.queryTrsServer"
                    @onError="onTrsSelectionError"
                    @onTrsSelection="onTrsSelection" />
            </div>

            <BAlert v-if="isAutoImport && !hasErrorMessage" show variant="info">
                <LoadingSpan message="正在加载您的工作流" />
            </BAlert>
            <div v-else>
                <div class="my-3">
                    <BFormGroup label="TRS ID:" label-for="trs-id-input" label-class="font-weight-bold">
                        <BFormInput id="trs-id-input" v-model="toolId" debounce="500" />
                    </BFormGroup>
                </div>
                <div>
                    <BAlert v-if="loading" show variant="info">
                        <LoadingSpan :message="`正在加载 ${toolIdTrimmed}，这可能需要一些时间 - 请耐心等待`" />
                    </BAlert>

                    <BAlert :show="hasErrorMessage" variant="danger">
                        {{ errorMessage }}
                    </BAlert>

                    <BAlert v-if="importing" show variant="info">
                        <LoadingSpan message="正在导入工作流" />
                    </BAlert>
                </div>

                <TrsTool
                    v-if="trsTool"
                    :trs-tool="trsTool"
                    @onImport="(versionId) => importVersion(trsSelection?.id, trsTool?.id, versionId)" />
            </div>

            <hr />

            <div>
                <TrsUrlImport
                    :query-trs-url="props.queryTrsUrl"
                    @onImport="(url) => importVersionFromUrl(url, isRun)" />
            </div>
        </BCard>
        <BAlert v-else class="text-center my-2" show variant="danger">
            匿名用户无法导入工作流，请注册或登录
        </BAlert>
    </div>
</template>
