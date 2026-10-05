<script setup lang="ts">
import PageContainer from "@/components/PageContainer.vue"
import HelpSearch from "@/components/help/HelpSearch.vue"
import HelpInstall from "@/components/help/HelpInstall.vue"
import HelpPublish from "@/components/help/HelpPublish.vue"
import HelpCite from "@/components/help/HelpCite.vue"

const commonProps = { hAlign: "left" as "left" | "center" }
</script>
<template>
    <page-container>
        <div class="help-page-row">
            <div class="help-page-column" style="overflow: auto">
                <h2>Tool Shed Help</h2>
                <HelpSearch v-bind="commonProps" />
                <HelpInstall v-bind="commonProps" />
                <HelpPublish v-bind="commonProps" />
                <HelpCite v-bind="commonProps" />
            </div>
        </div>
    </page-container>
</template>

<style scoped>
.help-page-row {
    display: flex;
    flex-wrap: wrap;
    align-content: flex-start;
    align-items: flex-start;
    justify-content: center;
    width: 100%;
}

.help-page-column {
    width: 75%;
}
</style>
