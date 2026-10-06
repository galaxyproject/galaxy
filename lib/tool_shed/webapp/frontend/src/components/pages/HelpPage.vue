<script setup lang="ts">
import PageContainer from "@/components/PageContainer.vue"
import PageHeader from "@/components/PageHeader.vue"
import HelpSearch from "@/components/help/HelpSearch.vue"
import HelpInstall from "@/components/help/HelpInstall.vue"
import HelpPublish from "@/components/help/HelpPublish.vue"
import HelpCite from "@/components/help/HelpCite.vue"

const commonProps = { hAlign: "left" as "left" | "center" }
</script>
<template>
    <page-container>
        <template #header>
            <page-header
                title="Tool Shed Help"
                subtitle="Finding, installing, publishing, and citing the tools in the Galaxy Tool Shed."
            />
        </template>
        <div class="help-grid">
            <section class="help-card shed-card"><HelpSearch v-bind="commonProps" /></section>
            <section class="help-card shed-card"><HelpInstall v-bind="commonProps" /></section>
            <section class="help-card shed-card"><HelpPublish v-bind="commonProps" /></section>
            <section class="help-card shed-card"><HelpCite v-bind="commonProps" /></section>
        </div>
    </page-container>
</template>

<style scoped>
.help-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 24rem), 1fr));
    gap: 1.25rem;
}

.help-card {
    padding: 1.5rem;
}

/* The help sections size their icons for the old full-width layout; on cards they become small tiles */
.help-card :deep(.help-icon) {
    box-sizing: content-box;
    width: 1.15rem !important;
    height: 1.15rem;
    padding: 0.8rem;
    font-size: 1.15rem !important;
    color: var(--color-galaxy-primary);
    background: var(--color-bay-of-many-100, #edf4fa);
    border-radius: 0.6rem;
}

.help-card :deep(.help-align-left),
.help-card :deep(.help-align-center) {
    margin-top: 0.9rem;
    padding-bottom: 0;
    text-align: left;
    line-height: 1.6;
}

.help-card :deep(.help-heading) {
    margin: 0 0 0.4rem;
    font-size: 1.2rem;
}
</style>
