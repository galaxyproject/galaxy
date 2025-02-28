<script setup lang="ts">
import RecentlyCreatedRepositories from "@/components/RecentlyCreatedRepositories.vue"
import PageContainer from "@/components/PageContainer.vue"
import { notify } from "@/util"

interface LandingPageProps {
    message?: string | null
}

const props = defineProps<LandingPageProps>()
if (props.message != null) {
    notify(props.message, "info")
}
</script>

<template>
    <page-container>
        <div class="row justify-left">Welcome to the Galaxy Tool Shed.</div>
        <div class="row justify-center">
            <recently-created-repositories class="col-4" />
        </div>
    </page-container>
</template>
