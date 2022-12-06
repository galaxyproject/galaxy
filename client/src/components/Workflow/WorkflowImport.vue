<script setup>
import TrsImport from "./Import/TrsImport";
import TrsSearch from "./Import/TrsSearch";
import FromFileOrUrl from "./Import/FromFileOrUrl";
</script>

<template>
    <section>
        <h1 class="h-lg">Import workflow</h1>
        <b-tabs fill>
            <b-tab title="Archived file or url" active>
                <FromFileOrUrl />
            </b-tab>
            <b-tab title="GA4GH servers">
                <div class="mt-4">
                    <h2 class="h-sm">Import a Workflow from Configured GA4GH Tool Registry Servers (e.g. Dockstore)</h2>
                    <TrsSearch />
                </div>
            </b-tab>
            <b-tab title="TRS ID">
                <div class="mt-4">
                    <h2 class="h-sm">Import from a TRS ID</h2>
                    <TrsImport />
                </div>
            </b-tab>
        </b-tabs>
    </section>
</template>
