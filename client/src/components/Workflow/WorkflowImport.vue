<script setup lang="ts">
import { BButton, BCard, BCardBody, BCardTitle } from "bootstrap-vue";
import { ref } from "vue";

import FromFile from "@/components/Workflow/Import/FromFile.vue";
import FromUrl from "@/components/Workflow/Import/FromUrl.vue";
import TrsImport from "@/components/Workflow/Import/TrsImport.vue";

type ImportView = "cards" | "upload" | "fetch" | "repository";

const currentView = ref<ImportView>("cards");

function selectView(view: ImportView) {
    currentView.value = view;
}

function backToCards() {
    currentView.value = "cards";
}
</script>

<template>
    <section>
        <h1 class="h-lg">Import workflow</h1>

        <div v-if="currentView === 'cards'" class="row mx-auto" style="margin-top: 20vh; max-width: 1000px;">
            <div class="col-lg-4 mb-3 mx-auto" style="max-width: 300px;">
                <BCard class="h-100 workflow-import-file-link clickable-card" @click="selectView('upload')">
                    <BCardBody class="text-center">
                        <BCardTitle>Upload file</BCardTitle>
                        <p>Upload a *.ga file</p>
                    </BCardBody>
                </BCard>
            </div>

            <div class="col-lg-4 mb-3 mx-auto" style="max-width: 300px;">
                <BCard class="h-100 workflow-import-trs-search-link clickable-card" @click="selectView('fetch')">
                    <BCardBody class="text-center">
                        <BCardTitle>Fetch URL</BCardTitle>
                        <p>Fetch a remote *.ga file</p>
                    </BCardBody>
                </BCard>
            </div>

            <div class="col-lg-4 mb-3 mx-auto" style="max-width: 300px;">
                <BCard class="h-100 workflow-import-trs-id-link clickable-card" @click="selectView('repository')">
                    <BCardBody class="text-center">
                        <BCardTitle>Import from repository</BCardTitle>
                        <p>Like Dockstore or Workflow Hub</p>
                    </BCardBody>
                </BCard>
            </div>
        </div>

        <div v-else class="mt-4">
            <BButton variant="link" class="mb-3 p-0" @click="backToCards">
                &larr; Back to import options
            </BButton>

            <div v-if="currentView === 'upload'" class="my-5 mx-auto" style="max-width: 800px;">
                <FromFile />
            </div>

            <div v-if="currentView === 'fetch'" class="my-5 mx-auto" style="max-width: 800px;">
                <FromUrl />
            </div>

            <div v-if="currentView === 'repository'" class="my-5 mx-auto" style="max-width: 800px;">
                <TrsImport />
            </div>
        </div>
    </section>
</template>

<style scoped>
.clickable-card {
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}
.clickable-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}
</style>
