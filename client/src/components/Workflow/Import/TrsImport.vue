<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { Services } from "@/components/Workflow/services";
import { useUserStore } from "@/stores/userStore";

import type { TrsSelection } from "./types";

import LoadingSpan from "@/components/LoadingSpan.vue";
import TrsIdImport from "@/components/Workflow/Import/TrsIdImport.vue";
import TrsSearch from "@/components/Workflow/Import/TrsSearch.vue";
import TrsUrlImport from "@/components/Workflow/Import/TrsUrlImport.vue";

interface Props {
    isRun?: boolean;
    queryTrsId?: string;
    queryTrsUrl?: string;
    queryTrsServer?: string;
    queryTrsVersionId?: string;
    trsServers?: TrsSelection[];
    trsMethod?: "search" | "url" | "id";
}

const props = withDefaults(defineProps<Props>(), {
    trsMethod: "search",
    isRun: false,
    queryTrsId: '',
    queryTrsUrl: '',
    queryTrsServer: '',
    queryTrsVersionId: '',
    trsServers: () => [],
});

const emit = defineEmits<{
    (e: "input-valid", valid: boolean): void;
}>();

type TrsView = "trsId" | "trsUrl" | "trsSearch";

const { isAnonymous } = storeToRefs(useUserStore());
const importing = ref(false);
const errorMessage: Ref<string | null> = ref(null);
const trsSearchRef = ref<InstanceType<typeof TrsSearch>>();
const trsIdImportRef = ref<InstanceType<typeof TrsIdImport>>();
const trsUrlImportRef = ref<InstanceType<typeof TrsUrlImport>>();
const validationState = ref(false);

const services = new Services();
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

// In wizard mode: use trsMethod prop to determine which view to show
const effectiveView = computed<TrsView>(() => {
    // Map wizard method names to TrsView names
    const methodMap: Record<string, TrsView> = {
        search: "trsSearch",
        url: "trsUrl",
        id: "trsId",
    };
    return methodMap[props.trsMethod] || "trsSearch";
});

// Forward validation from child components
function onChildValidation(valid: boolean) {
    validationState.value = valid;
    emit("input-valid", valid);
}

// Expose import method for wizard
async function attemptImport() {
    // Delegate to the active view's import logic
    if (effectiveView.value === "trsSearch" && trsSearchRef.value) {
        trsSearchRef.value.triggerImport();
    } else if (effectiveView.value === "trsUrl" && trsUrlImportRef.value) {
        trsUrlImportRef.value.triggerImport();
    } else if (effectiveView.value === "trsId" && trsIdImportRef.value) {
        trsIdImportRef.value.triggerImport();
    }
}

defineExpose({ attemptImport });
</script>

<template>
    <div class="workflow-import-trs">
        <BAlert v-if="isAnonymous" class="text-center my-2" show variant="danger">
            Anonymous user cannot import workflows, please register or log in
        </BAlert>

        <div v-else>
            <BAlert v-if="importing" show variant="info">
                <LoadingSpan message="Importing workflow" />
            </BAlert>

            <BAlert v-if="errorMessage" show variant="danger">
                {{ errorMessage }}
            </BAlert>

            <div v-if="effectiveView === 'trsSearch'" style="min-height: 500px">
                <TrsSearch ref="trsSearchRef" @input-valid="onChildValidation" />
            </div>

            <div v-if="effectiveView === 'trsId'" style="min-height: 500px">
                <TrsIdImport
                    ref="trsIdImportRef"
                    :is-run="props.isRun"
                    :query-trs-id="props.queryTrsId"
                    :query-trs-server="props.queryTrsServer"
                    :query-trs-version-id="props.queryTrsVersionId"
                    @onImport="(trsId, toolId, version) => importVersion(trsId, toolId, version, props.isRun)"
                    @input-valid="onChildValidation" />
            </div>

            <div v-if="effectiveView === 'trsUrl'" style="min-height: 500px">
                <TrsUrlImport
                    ref="trsUrlImportRef"
                    :query-trs-url="props.queryTrsUrl"
                    @onImport="(url) => importVersionFromUrl(url, props.isRun)"
                    @input-valid="onChildValidation" />
            </div>
        </div>
    </div>
</template>

<style scoped>
.clickable-card {
    cursor: pointer;
    transition:
        transform 0.2s,
        box-shadow 0.2s;
}

.clickable-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}
</style>
