<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { Services } from "@/components/Workflow/services";
import { useUserStore } from "@/stores/userStore";

import type { TrsSelection } from "./types";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";
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
    mode?: "modal" | "wizard";
    trsMethod?: "cards" | "search" | "url" | "id";
}

const props = withDefaults(defineProps<Props>(), {
    mode: "modal",
    trsMethod: "cards",
});

const emit = defineEmits<{
    (e: "input-valid", valid: boolean): void;
}>();

type TrsView = "cards" | "trsId" | "trsUrl" | "trsSearch";

const currentView = ref<TrsView>("cards");
const { isAnonymous } = storeToRefs(useUserStore());
const importing = ref(false);
const errorMessage: Ref<string | null> = ref(null);
const trsSearchRef = ref<InstanceType<typeof TrsSearch>>();
const trsIdImportRef = ref<InstanceType<typeof TrsIdImport>>();
const trsUrlImportRef = ref<InstanceType<typeof TrsUrlImport>>();
const validationState = ref(false);

const services = new Services();
const router = useRouter();

function selectView(view: TrsView) {
    currentView.value = view;
}

function backToCards() {
    currentView.value = "cards";
}

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

// In modal mode: use internal currentView state
// In wizard mode: use trsMethod prop
const effectiveView = computed<TrsView>(() => {
    if (props.mode === "wizard") {
        // Map wizard method names to TrsView names
        const methodMap: Record<string, TrsView> = {
            cards: "cards",
            search: "trsSearch",
            url: "trsUrl",
            id: "trsId",
        };
        return methodMap[props.trsMethod] || "cards";
    }
    return currentView.value;
});

// Show card selection only in modal mode
const showCardSelection = computed(() => {
    return props.mode === "modal" && currentView.value === "cards";
});

// Show back button only in modal mode
const showBackButton = computed(() => {
    return props.mode === "modal" && currentView.value !== "cards";
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

// Auto-select view if query params are present (modal mode only)
if (props.mode === "modal") {
    if (props.queryTrsUrl) {
        currentView.value = "trsUrl";
    } else if (props.queryTrsId || props.queryTrsServer) {
        currentView.value = "trsId";
    }
}
</script>

<template>
    <div class="workflow-import-trs">
        <BAlert v-if="isAnonymous" class="text-center my-2" show variant="danger">
            Anonymous user cannot import workflows, please register or log in
        </BAlert>

        <div v-else>
            <div v-if="showCardSelection">
                <div class="my-5">
                    Workflows can be imported from TRS-compliant workflow registries using the GA4GH protocol. This
                    Galaxy server has {{ trsServers?.length || 0 }} configured TRS server(s):
                    <div class="text-center my-3">
                        <a
                            v-for="server in trsServers"
                            :key="server.id"
                            :href="server.link_url"
                            class="btn btn-primary m-2"
                            target="_blank"
                            rel="noopener noreferrer">
                            {{ server.label }}
                        </a>
                    </div>
                </div>

                <div class="row my-3">
                    <div class="col-xl-4 mb-3">
                        <GCard
                            class="h-100 workflow-import-trs-search-link clickable-card"
                            title="Search workflow registries"
                            @click="selectView('trsSearch')">
                            <p>Search for workflows across configured GA4GH servers.</p>
                        </GCard>
                    </div>

                    <div class="col-xl-4 mb-3">
                        <GCard
                            class="h-100 workflow-import-trs-id-link clickable-card"
                            title="TRS ID"
                            @click="selectView('trsId')">
                            <p>
                                <span>
                                    <FontAwesomeIcon
                                        :icon="faInfoCircle"
                                        tooltip
                                        title="A TRS ID can be obtained by visiting the website of the selected TRS server." />
                                </span>
                                When you know the TRS ID for a workflow in one of the configured GA4GH servers.
                            </p>
                        </GCard>
                    </div>

                    <div class="col-xl-4 mb-3">
                        <GCard
                            class="h-100 workflow-import-trs-url-link clickable-card"
                            title="TRS URL"
                            @click="selectView('trsUrl')">
                            <p>Import directly from any GA4GH server with a TRS URL.</p>
                        </GCard>
                    </div>
                </div>
            </div>

            <div v-else>
                <GButton v-if="showBackButton" color="grey" class="mb-5 p-0" @click="backToCards">
                    &larr; Back to TRS import options
                </GButton>

                <BAlert v-if="importing" show variant="info">
                    <LoadingSpan message="Importing workflow" />
                </BAlert>

                <BAlert v-if="errorMessage" show variant="danger">
                    {{ errorMessage }}
                </BAlert>

                <div v-if="effectiveView === 'trsSearch'" style="min-height: 500px">
                    <TrsSearch ref="trsSearchRef" :mode="props.mode" @input-valid="onChildValidation" />
                </div>

                <div v-if="effectiveView === 'trsId'" style="min-height: 500px">
                    <TrsIdImport
                        ref="trsIdImportRef"
                        :is-run="props.isRun"
                        :query-trs-id="props.queryTrsId"
                        :query-trs-server="props.queryTrsServer"
                        :query-trs-version-id="props.queryTrsVersionId"
                        :mode="props.mode"
                        @onImport="(trsId, toolId, version) => importVersion(trsId, toolId, version, props.isRun)"
                        @input-valid="onChildValidation" />
                </div>

                <div v-if="effectiveView === 'trsUrl'" style="min-height: 500px">
                    <TrsUrlImport
                        ref="trsUrlImportRef"
                        :query-trs-url="props.queryTrsUrl"
                        :mode="props.mode"
                        @onImport="(url) => importVersionFromUrl(url, props.isRun)"
                        @input-valid="onChildValidation" />
                </div>
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
