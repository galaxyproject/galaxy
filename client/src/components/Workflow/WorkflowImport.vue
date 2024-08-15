<script setup lang="ts">
import { BTab, BTabs } from "bootstrap-vue";

import FromFileOrUrl from "@/components/Workflow/Import/FromFileOrUrl.vue";
import TrsImport from "@/components/Workflow/Import/TrsImport.vue";
import TrsSearch from "@/components/Workflow/Import/TrsSearch.vue";
</script>

<template>
    <section>
        <h1 class="h-lg">Import workflow</h1>
        <BTabs fill>
            <BTab title-link-class="workflow-import-file-link" title="Archived file or url" active>
                <FromFileOrUrl />
            </BTab>

            <BTab title-link-class="workflow-import-trs-search-link" title="GA4GH servers">
                <div class="mt-4">
                    <h2 class="h-sm">Import a Workflow from Configured GA4GH Tool Registry Servers (e.g. Dockstore)</h2>

                    <TrsSearch />
                </div>
            </BTab>

            <BTab title-link-class="workflow-import-trs-id-link" title="TRS ID">
                <div class="mt-4">
                    <h2 class="h-sm">Import from a TRS ID</h2>

                    <TrsImport />
                </div>
            </BTab>
        </BTabs>
    </section>
</template>
