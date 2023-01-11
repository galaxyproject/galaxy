<script setup lang="ts">
import TrsTool from "./TrsTool.vue";
import TrsUrlImport from "./TrsUrlImport.vue";
import { Toast } from "@/composables/toast";
import { Services } from "../services";
import { getGalaxyInstance } from "@/app";
import { computed, ref, watch, type Ref } from "vue";
import { getRedirectOnImportPath } from "../redirectPath";
import LoadingSpan from "@/components/LoadingSpan.vue";
import TrsServerSelection from "./TrsServerSelection.vue";
import { useRouter } from "vue-router/composables";
import type { TrsSelection, TrsTool as TrsToolInterface } from "./types";

const props = defineProps({
    queryTrsServer: {
        type: String,
        default: null,
    },
    queryTrsId: {
        type: String,
        default: null,
    },
    queryTrsVersionId: {
        type: String,
        default: null,
    },
    queryTrsUrl: {
        type: String,
        default: null,
    },
    isRun: {
        type: Boolean,
        default: false,
    },
});

const trsTool: Ref<TrsToolInterface | null> = ref(null);
const loading = ref(false);
const importing = ref(false);
const trsSelection: Ref<TrsSelection | null> = ref(null);
const errorMessage: Ref<string | null> = ref(null);
const toolId = ref(props.queryTrsId);
const isAnonymous: Ref<boolean> = getGalaxyInstance().user?.isAnonymous();
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
                importVersion(trsSelection.value.id, trsTool.value!.id, version[versionField], props.isRun);
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

const router = useRouter();

async function importVersion(trsId?: string, toolIdToImport?: string, version?: string, isRunFormRedirect = false) {
    if (!trsId || !toolIdToImport) {
        errorMessage.value = "Import Failed. Unknown Id";
        return;
    }

    importing.value = true;
    errorMessage.value = null;

    try {
        const response = await services.importTrsTool(trsId, toolIdToImport, version);
        const path = getRedirectOnImportPath(response, isRunFormRedirect);

        router.push(path);
    } catch (error) {
        errorMessage.value = (error as string) || "Import failed for an unknown reason.";
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
        errorMessage.value = (error as string) || "Import failed for an unknown reason.";
    } finally {
        importing.value = false;
    }
}
</script>

<template>
    <div>
        <b-card v-if="!isAnonymous" title="GA4GH Tool Registry Server (TRS) Workflow Import">
            <div>
                <b>TRS Server:</b>
                <TrsServerSelection
                    :trs-selection="trsSelection"
                    :query-trs-server="props.queryTrsServer"
                    @onError="onTrsSelectionError"
                    @onTrsSelection="onTrsSelection" />
            </div>
            <b-alert v-if="isAutoImport && !hasErrorMessage" show variant="info">
                <LoadingSpan message="Loading your Workflow" />
            </b-alert>
            <div v-else>
                <div class="my-3">
                    <b-form-group label="TRS ID:" label-class="font-weight-bold">
                        <b-form-input id="trs-id-input" v-model="toolId" debounce="500" />
                    </b-form-group>
                </div>
                <div>
                    <b-alert v-if="loading" show variant="info">
                        <LoadingSpan :message="`Loading ${toolIdTrimmed}, this may take a while - please be patient`" />
                    </b-alert>
                    <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
                    <b-alert v-if="importing" show variant="info">
                        <LoadingSpan message="Importing workflow" />
                    </b-alert>
                </div>
                <TrsTool
                    v-if="trsTool"
                    :trs-tool="trsTool"
                    @onImport="(versionId) => importVersion(trsSelection?.id, trsTool?.id, versionId)" />
            </div>
            <hr />
            <div>
                <TrsUrlImport :query-trs-url="props.queryTrsUrl" @onImport="(url) => importVersionFromUrl(url)" />
            </div>
        </b-card>
        <b-alert v-else class="text-center my-2" show variant="danger">
            Anonymous user cannot import workflows, please register or log in
        </b-alert>
    </div>
</template>
