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
        <template #header>
            <landing-search-box />
        </template>

        <div class="landing-columns">
            <div class="landing-column-info">
                <h2 class="shed-section-title">Get started</h2>
                <landing-info-sections />
            </div>
            <div class="landing-column-recent">
                <recently-created-repositories />
            </div>
        </div>
    </page-container>
</template>

<style scoped>
.landing-columns {
    display: grid;
    gap: 2rem;
    padding-top: 0.75rem;
}

@media (min-width: 1024px) {
    .landing-columns {
        grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
        align-items: start;
    }
}
</style>
