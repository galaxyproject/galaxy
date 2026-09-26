<script setup lang="ts">
import RecentlyCreatedRepositories from "@/components/RecentlyCreatedRepositories.vue"
import PageContainer from "@/components/PageContainer.vue"
import LandingSearchBox from "@/components/LandingSearchBox.vue"
import LandingInfoSections from "@/components/LandingInfoSections.vue"
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
        <landing-search-box />

        <div class="landing-content">
            <div class="row q-mt-lg q-col-gutter-lg justify-center">
                <div class="col-12 col-md-4">
                    <landing-info-sections />
                </div>
                <div class="col-12 col-md-5">
                    <recently-created-repositories />
                </div>
            </div>
        </div>
    </page-container>
</template>

<style scoped>
.landing-content {
    max-width: 1200px;
    margin: 0 auto;
}
</style>
