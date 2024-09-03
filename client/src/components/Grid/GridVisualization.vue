<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { BNav, BNavItem } from "bootstrap-vue";

import visualizationsGridConfig from "@/components/Grid/configs/visualizations";
import visualizationsPublishedGridConfig from "@/components/Grid/configs/visualizationsPublished";
import { useUserStore } from "@/stores/userStore";

import Heading from "@/components/Common/Heading.vue";
import LoginRequired from "@/components/Common/LoginRequired.vue";
import GridList from "@/components/Grid/GridList.vue";

const userStore = useUserStore();

library.add(faPlus);

interface Props {
    activeList?: "my" | "published";
}

withDefaults(defineProps<Props>(), {
    activeList: "my",
});
</script>

<template>
    <div class="d-flex flex-column">
        <div class="d-flex">
            <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Visualizations</Heading>
        </div>
        <BNav pills justified class="mb-2">
            <BNavItem
                id="visualizations-my-tab"
                :active="activeList === 'my'"
                :disabled="userStore.isAnonymous"
                to="/visualizations/list">
                My Visualizations
                <LoginRequired
                    v-if="userStore.isAnonymous"
                    target="visualizations-my-tab"
                    title="Manage your Visualizations" />
            </BNavItem>
            <BNavItem :active="activeList === 'published'" to="/visualizations/list_published">
                Public Visualizations
            </BNavItem>
        </BNav>
        <GridList v-if="activeList === 'my'" :grid-config="visualizationsGridConfig" embedded />
        <GridList v-else :grid-config="visualizationsPublishedGridConfig" embedded />
    </div>
</template>
