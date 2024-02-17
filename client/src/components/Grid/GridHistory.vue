<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus, faStar, faTrash } from "@fortawesome/free-solid-svg-icons";
import { BNav, BNavItem } from "bootstrap-vue";

import historiesGridConfig from "@/components/Grid/configs/histories";
import historiesPublishedGridConfig from "@/components/Grid/configs/historiesPublished";
import historiesSharedGridConfig from "@/components/Grid/configs/historiesShared";

import Heading from "@/components/Common/Heading.vue";
import GridList from "@/components/Grid/GridList.vue";

library.add(faPlus, faStar, faTrash);

interface Props {
    activeList?: "my" | "shared" | "published";
}

withDefaults(defineProps<Props>(), {
    activeList: "my",
});
</script>

<template>
    <div>
        <div class="mb-2">
            <div class="d-flex">
                <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Histories</Heading>
                <div>
                    <BButton size="sm" variant="outline-primary" to="/histories/import">
                        <Icon :icon="faPlus" />
                        <span v-localize>Import New History</span>
                    </BButton>
                </div>
            </div>
            <BNav pills justified class="mb-2">
                <BNavItem :active="activeList === 'my'" to="/histories/list"> My Histories </BNavItem>
                <BNavItem :active="activeList === 'shared'" to="/histories/list_shared"> Shared with Me </BNavItem>
                <BNavItem :active="activeList === 'published'" to="/histories/list_published">
                    Public Histories
                </BNavItem>
            </BNav>
            <GridList v-if="activeList === 'my'" :grid-config="historiesGridConfig" embedded />
            <GridList v-else-if="activeList === 'shared'" :grid-config="historiesSharedGridConfig" embedded />
            <GridList v-else :grid-config="historiesPublishedGridConfig" embedded />
        </div>
    </div>
</template>
