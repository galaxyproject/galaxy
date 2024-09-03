<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { BNav, BNavItem } from "bootstrap-vue";

import historiesGridConfig from "@/components/Grid/configs/histories";
import historiesPublishedGridConfig from "@/components/Grid/configs/historiesPublished";
import historiesSharedGridConfig from "@/components/Grid/configs/historiesShared";
import { useUserStore } from "@/stores/userStore";

import Heading from "@/components/Common/Heading.vue";
import LoginRequired from "@/components/Common/LoginRequired.vue";
import GridList from "@/components/Grid/GridList.vue";
import HistoryArchive from "@/components/History/Archiving/HistoryArchive.vue";

const userStore = useUserStore();

library.add(faPlus);

interface Props {
    activeList?: "archived" | "my" | "shared" | "published";
    username?: string;
}

const props = withDefaults(defineProps<Props>(), {
    activeList: "my",
    username: undefined,
});
</script>

<template>
    <div class="d-flex flex-column">
        <div class="d-flex">
            <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Histories</Heading>
            <div v-if="!userStore.isAnonymous">
                <BButton
                    size="sm"
                    variant="outline-primary"
                    to="/histories/import"
                    data-description="grid action import new history">
                    <Icon :icon="faPlus" />
                    <span v-localize>Import History</span>
                </BButton>
            </div>
        </div>
        <BNav pills justified class="mb-2">
            <BNavItem
                id="histories-my-tab"
                :active="activeList === 'my'"
                :disabled="userStore.isAnonymous"
                to="/histories/list">
                My Histories
                <LoginRequired v-if="userStore.isAnonymous" target="histories-my-tab" title="Manage your Histories" />
            </BNavItem>
            <BNavItem
                id="histories-shared-tab"
                :active="activeList === 'shared'"
                :disabled="userStore.isAnonymous"
                to="/histories/list_shared">
                Shared with Me
                <LoginRequired
                    v-if="userStore.isAnonymous"
                    target="histories-shared-tab"
                    title="Manage your Histories" />
            </BNavItem>
            <BNavItem id="histories-published-tab" :active="activeList === 'published'" to="/histories/list_published">
                Public Histories
            </BNavItem>
            <BNavItem
                id="histories-archived-tab"
                :active="activeList === 'archived'"
                :disabled="userStore.isAnonymous"
                to="/histories/archived">
                Archived Histories
                <LoginRequired
                    v-if="userStore.isAnonymous"
                    target="histories-archived-tab"
                    title="Manage your Histories" />
            </BNavItem>
        </BNav>
        <GridList v-if="activeList === 'my'" :grid-config="historiesGridConfig" embedded />
        <GridList v-else-if="activeList === 'shared'" :grid-config="historiesSharedGridConfig" embedded />
        <GridList
            v-else-if="activeList === 'published'"
            :grid-config="historiesPublishedGridConfig"
            :username-search="props.username"
            embedded />
        <HistoryArchive v-else />
    </div>
</template>
