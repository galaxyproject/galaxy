<script setup lang="ts">
import { BAlert, BFormGroup, BFormInput } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";

import { Services } from "@/components/Workflow/services";
import { Toast } from "@/composables/toast";

import type { TrsSelection, TrsTool as TrsToolInterface } from "./types";

import LoadingSpan from "@/components/LoadingSpan.vue";
import TrsServerSelection from "@/components/Workflow/Import/TrsServerSelection.vue";
import TrsTool from "@/components/Workflow/Import/TrsTool.vue";

interface Props {
    isRun?: boolean;
    queryTrsId?: string;
    queryTrsServer?: string;
    queryTrsVersionId?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onImport", trsId: string, toolId: string, version?: string): void;
}>();

const trsTool: Ref<TrsToolInterface | null> = ref(null);
const loading = ref(false);
const trsSelection: Ref<TrsSelection | null> = ref(null);
const errorMessage: Ref<string | null> = ref(null);
const toolId = ref(props.queryTrsId);
const isAutoImport = ref(Boolean(props.queryTrsVersionId && props.queryTrsServer && props.queryTrsId));

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
                importVersion(trsSelection.value.id, trsTool.value!.id, version[versionField]);
            } else {
                Toast.warning(`Specified version: ${props.queryTrsVersionId} doesn't exist`);
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

function importVersion(trsId: string, toolIdToImport: string, version?: string) {
    emit("onImport", trsId, toolIdToImport, version);
}
</script>

<template>
    <div class="workflow-import-trs-id">
        <h2 class="h-sm">Import from TRS ID</h2>

        <div>
            <b>TRS Server:</b>

            <TrsServerSelection
                :trs-selection="trsSelection"
                :query-trs-server="props.queryTrsServer"
                @onError="onTrsSelectionError"
                @onTrsSelection="onTrsSelection" />
        </div>

        <BAlert v-if="isAutoImport && !hasErrorMessage" show variant="info">
            <LoadingSpan message="Loading your Workflow" />
        </BAlert>
        <div v-else>
            <div class="my-3">
                <BFormGroup
                    :label="`Enter a ${trsSelection?.label} TRS ID:`"
                    label-for="trs-id-input"
                    label-class="font-weight-bold">
                    <BFormInput id="trs-id-input" v-model="toolId" debounce="500" />
                </BFormGroup>
            </div>
            <div>
                <BAlert v-if="loading" show variant="info">
                    <LoadingSpan :message="`Loading ${toolIdTrimmed}, this may take a while - please be patient`" />
                </BAlert>

                <BAlert :show="hasErrorMessage" variant="danger">
                    {{ errorMessage }}
                </BAlert>
            </div>

            <TrsTool
                v-if="trsTool"
                :trs-tool="trsTool"
                @onImport="(versionId) => importVersion(trsSelection?.id || '', trsTool?.id || '', versionId)" />
        </div>
    </div>
</template>
