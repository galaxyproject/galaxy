<script setup lang="ts">
import RecentlyCreatedRepositories from "@/components/RecentlyCreatedRepositories.vue"
import PageContainer from "@/components/PageContainer.vue"
import LandingCarousel from "@/components/LandingCarousel.vue"
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
        <div class="row justify-center">
            <div class="col-8">
                <h2>Welcome to the Galaxy Tool Shed</h2>
                <p class="text-body1">
                    The Galaxy Tool Shed contains thousands of published Galaxy tools to enable cutting edge research.
                    The tool shed being constantly updated by the Galaxy community with new tools, updates to tools as
                    new versions of software are released, and bug fixes.
                </p>
            </div>
        </div>

        <div class="row justify-center">
            <div class="col-4">
                <LandingCarousel />
            </div>
            <recently-created-repositories class="col-4" />
        </div>
    </page-container>
</template>
