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
        <div class="fit row wrap justify-center items-start content-start">
            <div class="col-9" style="overflow: auto">
                <h2>Tool Shed Help</h2>
                <HelpSearch v-bind="commonProps" />
                <HelpInstall v-bind="commonProps" />
                <HelpPublish v-bind="commonProps" />
                <HelpCite v-bind="commonProps" />
            </div>
        </div>
    </page-container>
</template>
