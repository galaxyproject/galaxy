<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faQuestion, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BAlert, BButton, BCard, BFormInput, BInputGroup, BInputGroupAppend, BTable } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { Services } from "@/components/Workflow/services";
import { withPrefix } from "@/utils/redirect";

import type { TrsSelection } from "./types";

import LoadingSpan from "@/components/LoadingSpan.vue";
import TrsServerSelection from "@/components/Workflow/Import/TrsServerSelection.vue";
import TrsTool from "@/components/Workflow/Import/TrsTool.vue";

library.add(faQuestion, faTimes);

type TrsSearchData = {
    id: string;
    name: string;
    description: string;
    [key: string]: unknown;
};

const fields = [
    { key: "name", label: "名称" },
    { key: "description", label: "描述" },
    { key: "organization", label: "组织" },
];

const query = ref("");
const results: Ref<TrsSearchData[]> = ref([]);
const trsServer = ref("");
const loading = ref(false);
const importing = ref(false);
const trsSelection: Ref<TrsSelection | null> = ref(null);
const errorMessage: Ref<string | null> = ref(null);

const hasErrorMessage = computed(() => {
    return errorMessage.value != null;
});

const itemsComputed = computed(() => {
    return computeItems(results.value);
});

const searchHelp = computed(() => {
    return "通过工作流描述进行搜索。可以使用标签（键:值）来搜索元数据 - 例如 name:example。可用标签包括组织和名称。";
});

const services = new Services();

watch(query, async () => {
    if (query.value == "") {
        results.value = [];
    } else {
        loading.value = true;

        try {
            const response = await axios.get(
                withPrefix(`/api/trs_search?query=${query.value}&trs_server=${trsServer.value}`)
            );
            results.value = response.data;
        } catch (e) {
            errorMessage.value = e as string;
        }

        loading.value = false;
    }
});

function onTrsSelection(selection: TrsSelection) {
    trsSelection.value = selection;
    trsServer.value = selection.id;
    query.value = "";
}

function onTrsSelectionError(message: string) {
    errorMessage.value = message;
}

function showRowDetails(row: BCard, index: number, e: MouseEvent) {
    if ((e.target as Node | undefined)?.nodeName !== "A") {
        row._showDetails = !row._showDetails;
    }
}

function computeItems(items: TrsSearchData[]) {
    return items.map((item) => {
        return {
            id: item.id,
            name: item.name,
            description: item.description,
            data: item,
            _showDetails: false,
        };
    });
}

const router = useRouter();

async function importVersion(trsId?: string, toolIdToImport?: string, version?: string, isRunFormRedirect = false) {
    if (!trsId || !toolIdToImport) {
        errorMessage.value = "导入失败。未知ID";
        return;
    }

    importing.value = true;
    errorMessage.value = null;

    try {
        const response = await services.importTrsTool(trsId, toolIdToImport, version);
        const path = getRedirectOnImportPath(response, isRunFormRedirect);

        router.push(path);
    } catch (e) {
        errorMessage.value = (e as string) || "导入因未知原因失败。";
    }

    importing.value = false;
}
</script>

<template>
    <BCard class="workflow-import-trs-search" title="GA4GH 工具注册服务器 (TRS) 工作流搜索">
        <BAlert :show="hasErrorMessage" variant="danger">
            {{ errorMessage }}
        </BAlert>

        <div class="mb-3">
            <b>TRS 服务器:</b>

            <TrsServerSelection
                :trs-selection="trsSelection"
                @onTrsSelection="onTrsSelection"
                @onError="onTrsSelectionError" />
        </div>

        <div>
            <BInputGroup class="mb-3">
                <BFormInput
                    id="trs-search-query"
                    v-model="query"
                    debounce="500"
                    placeholder="搜索查询"
                    data-description="过滤文本输入"
                    @keyup.esc="query = ''" />

                <BInputGroupAppend>
                    <BButton
                        v-b-tooltip
                        placement="bottom"
                        size="sm"
                        data-description="显示帮助开关"
                        :title="searchHelp">
                        <FontAwesomeIcon :icon="faQuestion" />
                    </BButton>

                    <BButton size="sm" title="清空搜索" @click="query = ''">
                        <FontAwesomeIcon :icon="faTimes" />
                    </BButton>
                </BInputGroupAppend>
            </BInputGroup>
        </div>

        <div>
            <BAlert v-if="loading" variant="info" show>
                <LoadingSpan :message="`正在搜索 ${query}，这可能需要一些时间 - 请耐心等待`" />
            </BAlert>
            <BAlert v-else-if="!query" variant="info" show> 输入搜索查询以开始搜索。 </BAlert>
            <BAlert v-else-if="results.length == 0" variant="info" show>
                未找到搜索结果，请完善您的搜索条件。
            </BAlert>
            <BTable
                v-else
                :fields="fields"
                :items="itemsComputed"
                hover
                striped
                caption-top
                :busy="loading"
                @row-clicked="showRowDetails">
                <template v-slot:row-details="row">
                    <BCard>
                        <BAlert v-if="importing" variant="info" show>
                            <LoadingSpan message="正在导入工作流" />
                        </BAlert>

                        <TrsTool
                            :trs-tool="row.item.data"
                            @onImport="(versionId) => importVersion(trsSelection?.id, row.item.data.id, versionId)" />
                    </BCard>
                </template>
            </BTable>
        </div>
    </BCard>
</template>
