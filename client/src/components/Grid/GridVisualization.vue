<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { BNav, BNavItem } from "bootstrap-vue";

import visualizationsGridConfig from "@/components/Grid/configs/visualizations";
import visualizationsPublishedGridConfig from "@/components/Grid/configs/visualizationsPublished";

import Heading from "@/components/Common/Heading.vue";
import GridList from "@/components/Grid/GridList.vue";

library.add(faPlus);

interface Props {
    activeList?: "my" | "published";
}

withDefaults(defineProps<Props>(), {
    activeList: "my",
});
</script>

<template>
    <div>
        <div class="mb-2">
            <div class="d-flex">
                <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Visualizations</Heading>
                <div>
                    <BButton size="sm" variant="outline-primary" to="/visualizations">
                        <Icon :icon="faPlus" />
                        <span v-localize>Create New Visualization</span>
                    </BButton>
                </div>
            </div>
            <BNav pills justified class="mb-2">
                <BNavItem :active="activeList === 'my'" to="/visualizations/list"> My Visualizations </BNavItem>
                <BNavItem :active="activeList === 'published'" to="/visualizations/list_published">
                    Public Visualizations
                </BNavItem>
            </BNav>
            <GridList v-if="activeList === 'my'" :grid-config="visualizationsGridConfig" embedded />
            <GridList v-else :grid-config="visualizationsPublishedGridConfig" embedded />
        </div>
    </div>
</template>
