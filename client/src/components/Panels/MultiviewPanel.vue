<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faColumns, faPlus, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge, BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { HistoriesFilters } from "@/components/History/HistoriesFilters";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { localize } from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import FilterMenu from "@/components/Common/FilterMenu.vue";
import HistoryList from "@/components/History/HistoryScrollList.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const route = useRoute();
const router = useRouter();

library.add(faColumns, faPlus, faUndo);

const filter = ref("");
const showAdvanced = ref(false);
const loading = ref(false);

const isAnonymous = computed(() => useUserStore().isAnonymous);
const historyStore = useHistoryStore();
const { historiesLoading, currentHistoryId } = storeToRefs(historyStore);

const pinnedHistoryCount = computed(() => {
    return Object.keys(historyStore.pinnedHistories).length;
});
const pinRecentTitle = computed(() => {
    if (pinnedHistoryCount.value > 0) {
        return localize("重置选择以显示4个最近更新的历史记录");
    } else {
        return localize("当前在多视图中显示4个最近更新的历史记录");
    }
});

const pinRecentText = computed(() => {
    if (pinnedHistoryCount.value > 1) {
        return localize(`已固定${pinnedHistoryCount.value}个历史记录。点击此处重置`);
    } else if (pinnedHistoryCount.value == 1) {
        return localize("已固定1个历史记录。点击此处重置");
    } else {
        return localize("选择历史记录以固定到多视图");
    }
});

async function createAndPin() {
    try {
        loading.value = true;
        await historyStore.createNewHistory();
        if (!currentHistoryId.value) {
            throw new Error("创建历史记录时出错");
        }
        if (pinnedHistoryCount.value > 0) {
            historyStore.pinHistory(currentHistoryId.value);
        }
        router.push("/histories/view_multiple");
    } catch (error: any) {
        console.error(error);
        Toast.error(errorMessageAsString(error), "创建并固定历史记录时出错");
    } finally {
        loading.value = false;
    }
}

/** Reset to _default_ state; showing 4 latest updated histories */
function pinRecent() {
    historyStore.pinnedHistories = [];
    Toast.info(
        "在多视图中显示4个最近更新的历史记录。通过在面板中选择历史记录来将它们固定到历史记录多视图。",
        "历史记录多视图"
    );
}

function setFilter(newFilter: string, newValue: string) {
    filter.value = HistoriesFilters.setFilterValue(filter.value, newFilter, newValue);
}

function userTitle(title: string) {
    if (isAnonymous.value == true) {
        return `登录以${title}`;
    } else {
        return title;
    }
}
</script>

<template>
    <ActivityPanel title="选择历史记录">
        <template v-slot:header-buttons>
            <BButtonGroup>
                <BButton
                    v-b-tooltip.bottom.hover
                    data-description="为多视图创建新历史记录"
                    size="sm"
                    variant="link"
                    :title="userTitle('创建新历史记录并在多视图中显示')"
                    :disabled="isAnonymous"
                    @click="createAndPin">
                    <FontAwesomeIcon :icon="faPlus" fixed-width />
                </BButton>
            </BButtonGroup>
        </template>

        <template v-slot:header>
            <FilterMenu
                name="历史记录"
                placeholder="搜索历史记录"
                :filter-class="HistoriesFilters"
                :filter-text.sync="filter"
                :loading="historiesLoading || loading"
                :show-advanced.sync="showAdvanced" />
            <section v-if="!showAdvanced">
                <BButtonGroup
                    v-if="route.path === '/histories/view_multiple'"
                    v-b-tooltip.hover.noninteractive.bottom
                    class="w-100 mt-2"
                    :aria-label="pinRecentTitle"
                    :title="pinRecentTitle">
                    <BButton size="sm" :disabled="!pinnedHistoryCount" @click="pinRecent">
                        <span class="position-relative">
                            <FontAwesomeIcon v-if="pinnedHistoryCount" :icon="faUndo" class="mr-1" />
                            <b>{{ pinRecentText }}</b>
                        </span>
                    </BButton>
                </BButtonGroup>
            </section>
        </template>

        <div v-if="isAnonymous">
            <BBadge class="alert-info w-100 mx-2">
                请<a :href="withPrefix('/login')">登录或注册</a>以创建多个历史记录。
            </BBadge>
        </div>

        <HistoryList v-show="!showAdvanced" multiple :filter="filter" :loading.sync="loading" @setFilter="setFilter" />
    </ActivityPanel>
</template>
