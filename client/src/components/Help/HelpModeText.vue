<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCaretUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BCard, BCardBody, BCardHeader, BCollapse, BTab, BTabs } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, watch } from "vue";
import { useRoute } from "vue-router/composables";

import { useMarkdown } from "@/composables/markdown";
import { DEFAULT_HELP_TEXT, useHelpModeStore } from "@/stores/helpmode/helpModeStore";
import localize from "@/utils/localization";

import Heading from "../Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faCaretDown, faCaretUp);

const props = defineProps<{
    tabbed?: boolean;
}>();

const route = useRoute();

const tabNo = computed<number>({
    get: () => {
        if (activeTab.value) {
            return currentTabs.value.indexOf(activeTab.value);
        } else {
            return currentTabs.value.length - 1;
        }
    },
    set: (value: number) => {
        if (value === null) {
            activeTab.value = null;
        } else {
            activeTab.value = currentTabs.value[value] || null;
        }
    },
});

const { renderMarkdown } = useMarkdown({
    openLinksInNewPage: true,
    html: true,
    appendHrRuleToDetails: true,
    replaceCodeWithIcon: true,
    removeContentBeforeFirstH1: true,
    internalRoute: "https://galaxyproject.org",
});

const helpModeStore = useHelpModeStore();
const { activeTab, contents, loading, currentTabs } = storeToRefs(helpModeStore);

const currentRoute = computed(() => route.path);

watch(
    () => currentRoute.value,
    async (newVal) => {
        await helpModeStore.storeHelpModeTextForRoute(newVal);
    },
    { immediate: true }
);

const noHelpTextMsg = localize("No help text available for this component");

function changeTab(helpId: string) {
    if (activeTab.value === helpId && !props.tabbed) {
        activeTab.value = null;
    } else {
        activeTab.value = helpId;
    }
}
</script>

<template>
    <span v-if="currentTabs.length === 0" v-localize class="help-mode-container">{{ DEFAULT_HELP_TEXT }}</span>
    <component
        :is="props.tabbed ? BTabs : 'div'"
        v-else
        v-model="tabNo"
        class="d-flex flex-column help-mode-container"
        pills
        fill
        title-link-class="w-100 h-100 bg-danger"
        content-class="overflow-auto"
        nav-class="help-mode-tabs">
        <component :is="props.tabbed ? BTab : BCard" v-for="helpId of currentTabs" :key="helpId" no-body>
            <BCardHeader
                v-if="!props.tabbed"
                role="button"
                class="unselectable d-flex justify-content-between"
                @click="changeTab(helpId)">
                <Heading h3 size="sm" inline :icon="contents[helpId]?.icon" class="truncate">{{ contents[helpId]?.title }}</Heading>
                <FontAwesomeIcon :icon="activeTab === helpId ? faCaretUp : faCaretDown" />
            </BCardHeader>
            <template v-slot:title>
                <FontAwesomeIcon v-if="contents[helpId]?.icon" :icon="contents[helpId]?.icon" />
                {{ contents[helpId]?.title }}
            </template>

            <BCollapse :visible="activeTab && activeTab === helpId">
                <BCardBody class="pt-1">
                    <!-- eslint-disable-next-line vue/no-v-html -->
                    <div v-if="!loading" v-html="renderMarkdown(contents[helpId]?.content || noHelpTextMsg)" />
                    <BAlert v-else variant="info" show>
                        <LoadingSpan message="Loading help text" />
                    </BAlert>
                </BCardBody>
            </BCollapse>
        </component>
    </component>
</template>

<style>
.help-mode-tabs {
    overflow-x: auto;
    flex-wrap: unset;
    text-wrap: nowrap;
}
</style>

<style scoped lang="scss">
.help-mode-container {
    margin-top: 0;
    overflow-y: auto;
    height: 100%;
}
.truncate {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
