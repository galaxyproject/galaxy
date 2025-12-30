<script setup lang="ts">
import { BButton, BCard, BCardBody, BCardTitle } from "bootstrap-vue";
import { computed, type Ref, ref } from "vue";
import { useRoute } from "vue-router/composables";

import type { TrsSelection } from "@/components/Workflow/Import/types";
import { Services } from "@/components/Workflow/services";

import FromFile from "@/components/Workflow/Import/FromFile.vue";
import FromUrl from "@/components/Workflow/Import/FromUrl.vue";
import TrsImport from "@/components/Workflow/Import/TrsImport.vue";

type ImportView = "cards" | "upload" | "fetch" | "repository";

const route = useRoute();
const currentView = ref<ImportView>("cards");
const trsServers: Ref<TrsSelection[]> = ref([]);

const queryParams = computed(() => ({
    trsId: route.query.trs_id as string | undefined,
    trsUrl: route.query.trs_url as string | undefined,
    trsServer: route.query.trs_server as string | undefined,
    trsVersionId: route.query.trs_version_id as string | undefined,
    isRun: route.query.run_form === "true",
}));

function selectView(view: ImportView) {
    currentView.value = view;
}

function backToCards() {
    currentView.value = "cards";
}

const services = new Services();
services.getTrsServers().then((res) => {
    trsServers.value = res;
});

// Auto-select view based on query parameters
if (queryParams.value.trsId || queryParams.value.trsUrl || queryParams.value.trsServer) {
    currentView.value = "repository";
}
</script>

<template>
    <section>
        <h1 class="h-lg">Import workflow</h1>

        <div class="page-centered">
            <div v-if="currentView === 'cards'" class="row mx-auto" style="max-width: 1000px">
                <div class="col-lg-4 mb-3 mx-auto" style="max-width: 300px">
                    <BCard class="h-100 workflow-import-file-link clickable-card text-center" @click="selectView('upload')">
                        <BCardTitle>Upload file</BCardTitle>
                        <BCardBody>
                            <p class="text-muted">Upload a <code>*.ga</code> file from your computer</p>
                        </BCardBody>
                    </BCard>
                </div>

                <div class="col-lg-4 mb-3 mx-auto" style="max-width: 300px">
                    <BCard class="h-100 workflow-import-trs-search-link clickable-card text-center" @click="selectView('fetch')">
                        <BCardTitle>Fetch URL</BCardTitle>
                        <BCardBody>
                            <p class="text-muted">
                                Fetch a remote <code>*.ga</code> file from any publicly accessible URL.
                            </p>
                        </BCardBody>
                    </BCard>
                </div>

                <div class="col-lg-4 mb-3 mx-auto" style="max-width: 300px">
                    <BCard class="h-100 workflow-import-trs-id-link clickable-card text-center" @click="selectView('repository')">
                        <BCardTitle>Import from repository</BCardTitle>
                        <BCardBody>
                            <p>
                                Import a workflow from a configured GA4GH server:
                            </p>
                            <ul class="text-left text-muted">
                                <li v-for="server in trsServers" :key="server.id">
                                    {{ server.label }}
                                </li>
                            </ul>
                        </BCardBody>
                    </BCard>
                </div>
            </div>

            <div v-else class="d-flex flex-column flex-1">

                <div
                    :class="currentView === 'repository' ? 'container-wide' : 'container-narrow'"
                >
                    <p class="mb-0">
                        <BButton variant="link" class="p-0" @click="backToCards"> &larr; Back to import options </BButton>
                    </p>
                    <FromFile v-if="currentView === 'upload'" />
                    <FromUrl v-if="currentView === 'fetch'" />
                    <TrsImport
                        v-if="currentView === 'repository'"
                        :trs-servers="trsServers"
                        :is-run="queryParams.isRun"
                        :query-trs-id="queryParams.trsId"
                        :query-trs-url="queryParams.trsUrl"
                        :query-trs-server="queryParams.trsServer"
                        :query-trs-version-id="queryParams.trsVersionId"
                    />
                </div>
            </div>
        </div>
    </section>
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
.page-centered {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 60vh;
    width: 100%;
}
.container-narrow {
    margin: 0 auto;
    width: 100%;
    max-width: 600px;
}
.container-wide {
    margin: 0 auto;
    width: 100%;
    max-width: min(1000px, 80vw);
}
</style>
