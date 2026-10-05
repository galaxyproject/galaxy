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
            <div class="landing-columns">
                <div class="landing-column landing-column-info">
                    <landing-info-sections />
                </div>
                <div class="landing-column landing-column-recent">
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

.landing-columns {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--spacing-6);
    margin-top: var(--spacing-6);
}

.landing-column {
    width: 100%;
}

@media (min-width: 1024px) {
    .landing-column-info {
        width: 33.3333%;
    }

    .landing-column-recent {
        width: 41.6667%;
    }
}
</style>
