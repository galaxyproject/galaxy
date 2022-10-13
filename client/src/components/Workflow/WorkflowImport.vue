<script setup>
import TrsImport from "./Import/TrsImport";
import TrsSearch from "./Import/TrsSearch";
import FromFileOrUrl from "./Import/FromFileOrUrl";
</script>

<template>
    <section>
        <h3>Import workflow</h3>
        <b-tabs fill>
            <b-tab title="Archived file or url" active>
                <FromFileOrUrl />
            </b-tab>
            <b-tab title="GA4GH servers">
                <div class="mt-4">
                    <h4>Import a Workflow from Configured GA4GH Tool Registry Servers (e.g. Dockstore)</h4>
                    <TrsSearch />
                </div>
            </b-tab>
            <b-tab title="TRS ID">
                <div class="mt-4">
                    <h4>Import from a TRS ID</h4>
                    <TrsImport />
                </div>
            </b-tab>
        </b-tabs>
    </section>
</template>
