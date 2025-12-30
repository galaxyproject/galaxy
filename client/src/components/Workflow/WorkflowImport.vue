<script setup lang="ts">
import { BButton, BCard, BCardBody, BCardTitle } from "bootstrap-vue";
import { type Ref, ref } from "vue";

import type { TrsSelection } from "@/components/Workflow/Import/types";
import { Services } from "@/components/Workflow/services";

import FromFile from "@/components/Workflow/Import/FromFile.vue";
import FromUrl from "@/components/Workflow/Import/FromUrl.vue";
import TrsImport from "@/components/Workflow/Import/TrsImport.vue";

type ImportView = "cards" | "upload" | "fetch" | "repository";

const currentView = ref<ImportView>("cards");
const trsServers: Ref<TrsSelection[]> = ref([]);

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
                            <p class="text-muted">Upload a *.ga file from your computer</p>
                        </BCardBody>
                    </BCard>
                </div>

                <div class="col-lg-4 mb-3 mx-auto" style="max-width: 300px">
                    <BCard class="h-100 workflow-import-trs-search-link clickable-card text-center" @click="selectView('fetch')">
                        <BCardTitle>Fetch URL</BCardTitle>
                        <BCardBody>
                            <p class="text-muted">
                                Fetch a remote *.ga file from any publicly accessible URL.
                            </p>
                        </BCardBody>
                    </BCard>
                </div>

                <div class="col-lg-4 mb-3 mx-auto" style="max-width: 300px">
                    <BCard class="h-100 workflow-import-trs-id-link clickable-card text-center" @click="selectView('repository')">
                        <BCardTitle>Import from repository</BCardTitle>
                        <BCardBody>
                            <ul class="text-left text-muted">
                                <li v-for="server in trsServers" :key="server.id">
                                    {{ server.label }}
                                </li>
                            </ul>
                        </BCardBody>
                    </BCard>
                </div>
            </div>

            <div v-else>
                <BButton variant="link" class="p-0" @click="backToCards"> &larr; Back to import options </BButton>

                <div v-if="currentView === 'upload'" class="container-narrow">
                    <FromFile />
                </div>

                <div v-if="currentView === 'fetch'" class="container-narrow">
                    <FromUrl />
                </div>

                <div v-if="currentView === 'repository'" class="container-narrow">
                    <TrsImport :trs-servers="trsServers"/>
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
    margin-top: 20vh;
}
.container-narrow {
    margin: 0 auto;
    min-width: 600px;
    max-width: 100%;
}
</style>
