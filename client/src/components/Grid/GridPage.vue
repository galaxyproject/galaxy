<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { BNav, BNavItem } from "bootstrap-vue";

import pagesGridConfig from "@/components/Grid/configs/pages";
import pagesPublishedGridConfig from "@/components/Grid/configs/pagesPublished";

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
    <div class="d-flex flex-column">
        <div class="d-flex">
            <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Pages</Heading>
            <div>
                <BButton size="sm" variant="outline-primary" to="/pages/create">
                    <Icon :icon="faPlus" />
                    <span v-localize>Create Page</span>
                </BButton>
            </div>
        </div>
        <BNav pills justified class="mb-2">
            <BNavItem :active="activeList === 'my'" to="/pages/list"> My Pages </BNavItem>
            <BNavItem :active="activeList === 'published'" to="/pages/list_published"> Public Pages </BNavItem>
        </BNav>
        <GridList v-if="activeList === 'my'" :grid-config="pagesGridConfig" embedded />
        <GridList v-else :grid-config="pagesPublishedGridConfig" embedded />
    </div>
</template>
