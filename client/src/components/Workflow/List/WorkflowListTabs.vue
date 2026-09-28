<script setup lang="ts">
import { BNav, BNavItem } from "bootstrap-vue";
import { computed } from "vue";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import LoginRequired from "@/components/Common/LoginRequired.vue";

type WorkflowListTab = "curated" | "my" | "shared_with_me" | "published";

interface TabDefinition {
    key: WorkflowListTab;
    // The element id is also the LoginRequired popper target and a Selenium selector,
    // so it is intentionally distinct from `key` and must not change.
    id: string;
    to: string;
    label: string;
    loginRequired: boolean;
}

interface Props {
    active: WorkflowListTab;
}

defineProps<Props>();

const userStore = useUserStore();
const { config, isConfigLoaded } = useConfig();

const tabs = computed<TabDefinition[]>(() => {
    const definitions: TabDefinition[] = [];

    const curatedSource = isConfigLoaded.value ? config.value.curated_workflows_source : undefined;
    if (curatedSource === "iwc" || curatedSource === "local") {
        definitions.push({
            key: "curated",
            id: "curated",
            to: "/workflows/list_curated",
            label: "Curated workflows",
            loginRequired: false,
        });
    }

    definitions.push(
        {
            key: "my",
            id: "my",
            to: "/workflows/list",
            label: "My workflows",
            loginRequired: true,
        },
        {
            key: "shared_with_me",
            id: "shared-with-me",
            to: "/workflows/list_shared_with_me",
            label: "Workflows shared with me",
            loginRequired: true,
        },
        {
            key: "published",
            id: "published",
            to: "/workflows/list_published",
            label: "Public workflows",
            loginRequired: false,
        },
    );

    return definitions;
});
</script>

<template>
    <BNav pills justified class="mb-2">
        <BNavItem
            v-for="tab in tabs"
            :id="tab.id"
            :key="tab.key"
            :active="active === tab.key"
            :disabled="tab.loginRequired && userStore.isAnonymous"
            :to="tab.to">
            <span>{{ localize(tab.label) }}</span>
            <LoginRequired
                v-if="tab.loginRequired && userStore.isAnonymous"
                :target="tab.id"
                title="Manage your workflows" />
        </BNavItem>
    </BNav>
</template>
