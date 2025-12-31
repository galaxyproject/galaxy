<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { BAlert, BButton, BCard, BCardBody, BCardTitle } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { type Ref, ref } from "vue";
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
}

const props = defineProps<Props>();

type TrsView = "cards" | "trsId" | "trsUrl" | "trsSearch";

const currentView = ref<TrsView>("cards");
const { isAnonymous } = storeToRefs(useUserStore());
const importing = ref(false);
const errorMessage: Ref<string | null> = ref(null);

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

// Auto-select view if query params are present
if (props.queryTrsUrl) {
    currentView.value = "trsUrl";
} else if (props.queryTrsId || props.queryTrsServer) {
    currentView.value = "trsId";
}
</script>

<template>

    <div class="workflow-import-trs">
        <BAlert v-if="isAnonymous" class="text-center my-2" show variant="danger">
            Anonymous user cannot import workflows, please register or log in
        </BAlert>

        <div v-else>
            <div v-if="currentView === 'cards'">
                <div class="my-5">
                    Workflows can be imported from TRS-compliant workflow registries using the GA4GH protocol. This Galaxy server has {{ trsServers?.length || 0 }} configured TRS server(s):
                    <div class="text-center my-3">
                        <a
                            v-for="server in trsServers"
                            :key="server.id"
                            :href="server.link_url"
                            class="btn btn-primary m-2"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            {{ server.label }}
                        </a>
                    </div>
                </div>

                <div class="row my-3">
                    <div class="col-xl-4 mb-3">
                        <BCard class="h-100 workflow-import-trs-search-link clickable-card" @click="selectView('trsSearch')">
                            <BCardBody class="text-center">
                                <BCardTitle>Search workflow registries</BCardTitle>
                                <p>Search for workflows across configured GA4GH servers.</p>
                            </BCardBody>
                        </BCard>
                    </div>

                    <div class="col-xl-4 mb-3">
                        <BCard class="h-100 workflow-import-trs-id-link clickable-card" @click="selectView('trsId')">
                            <BCardBody class="text-center">
                                <BCardTitle>TRS ID</BCardTitle>
                                <p>
                                    <span>
                                        <FontAwesomeIcon
                                            :icon="faInfoCircle"
                                            tooltip
                                            title="A TRS ID can be obtained by visiting the website of the selected TRS server."
                                        />
                                    </span>
                                    When you know the TRS ID for a workflow in one of the configured GA4GH servers.
                                </p>
                            </BCardBody>
                        </BCard>
                    </div>

                    <div class="col-xl-4 mb-3">
                        <BCard class="h-100 workflow-import-trs-url-link clickable-card" @click="selectView('trsUrl')">
                            <BCardBody class="text-center">
                                <BCardTitle>TRS URL</BCardTitle>
                                <p>Import directly from any GA4GH server with a TRS URL.</p>
                            </BCardBody>
                        </BCard>
                    </div>
                </div>
            </div>

            <div v-else>
                <BButton variant="link" class="mb-5 p-0" @click="backToCards">
                    &larr; Back to TRS import options
                </BButton>

                <BAlert v-if="importing" show variant="info">
                    <LoadingSpan message="Importing workflow" />
                </BAlert>

                <BAlert v-if="errorMessage" show variant="danger">
                    {{ errorMessage }}
                </BAlert>

                <div v-if="currentView === 'trsSearch'" style="min-height: 500px">
                    <TrsSearch />
                </div>

                <div v-if="currentView === 'trsId'" style="min-height: 500px">
                    <TrsIdImport
                        :is-run="props.isRun"
                        :query-trs-id="props.queryTrsId"
                        :query-trs-server="props.queryTrsServer"
                        :query-trs-version-id="props.queryTrsVersionId"
                        @onImport="(trsId, toolId, version) => importVersion(trsId, toolId, version, props.isRun)" />
                </div>

                <div v-if="currentView === 'trsUrl'" style="min-height: 500px">
                    <TrsUrlImport
                        :query-trs-url="props.queryTrsUrl"
                        @onImport="(url) => importVersionFromUrl(url, props.isRun)" />
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
