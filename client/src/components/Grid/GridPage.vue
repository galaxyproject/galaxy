<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { BNav, BNavItem } from "bootstrap-vue";

import pagesGridConfig from "@/components/Grid/configs/pages";
import pagesPublishedGridConfig from "@/components/Grid/configs/pagesPublished";
import { useUserStore } from "@/stores/userStore";

import Heading from "@/components/Common/Heading.vue";
import LoginRequired from "@/components/Common/LoginRequired.vue";
import GridList from "@/components/Grid/GridList.vue";

const userStore = useUserStore();

library.add(faPlus);

interface Props {
    activeList?: "my" | "published";
    username?: string;
}

const props = withDefaults(defineProps<Props>(), {
    activeList: "my",
});
</script>

<template>
    <div class="d-flex flex-column">
        <div class="d-flex">
            <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Pages</Heading>
            <div v-if="!userStore.isAnonymous">
                <BButton id="page-create" size="sm" variant="outline-primary" to="/pages/create">
                    <Icon :icon="faPlus" />
                    <span v-localize>Create Page</span>
                </BButton>
            </div>
        </div>
        <BNav pills justified class="mb-2">
            <BNavItem
                id="pages-my-tab"
                :active="activeList === 'my'"
                :disabled="userStore.isAnonymous"
                to="/pages/list">
                My Pages
                <LoginRequired v-if="userStore.isAnonymous" target="pages-my-tab" title="Manage your Pages" />
            </BNavItem>
            <BNavItem :active="activeList === 'published'" to="/pages/list_published"> Public Pages </BNavItem>
        </BNav>
        <GridList v-if="activeList === 'my'" :grid-config="pagesGridConfig" embedded />
        <GridList v-else :grid-config="pagesPublishedGridConfig" :username-search="props.username" embedded />
    </div>
</template>
