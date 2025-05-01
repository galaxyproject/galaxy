<script setup lang="ts">
import axios from "axios";
import Vue, { computed, type Ref, ref, watch } from "vue";

import { GalaxyApi, type MessageException } from "@/api";
import { fetchCollectionSummary } from "@/api/datasetCollections";
import { useToast } from "@/composables/toast";
import { useDatasetStore } from "@/stores/datasetStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import _l from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import {
    initializeObjectReferences,
    initializeObjectToHistoryRefs,
    updateReferences,
} from "./object-permission-composables";

import PermissionObjectType from "./PermissionObjectType.vue";
import SharingIndicator from "./SharingIndicator.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { getHistoryNameById, loadHistoryById } = useHistoryStore();
const { getStoredWorkflowNameByInstanceId, fetchWorkflowForInstanceId } = useWorkflowStore();
const { getDataset, fetchDataset } = useDatasetStore();

const toast = useToast();

interface ObjectPermissionsProps {
    markdownContent: string;
}

const props = defineProps<ObjectPermissionsProps>();

const referencedObjects = initializeObjectReferences();
const {
    referencedJobIds,
    referencedHistoryDatasetIds,
    referencedHistoryDatasetCollectionIds,
    referencedWorkflowIds,
    referencedInvocationIds,
} = referencedObjects;

// We mostly defer to history permissions for various objects. Track them and merge
// into histories IDs.
const { jobsToHistories, invocationsToHistories, historyDatasetCollectionsToHistories, historyIds } =
    initializeObjectToHistoryRefs(referencedObjects);

type ErrorString = string;
type AccessibleState = Boolean | null | ErrorString;
type AccessibleMapRef = Ref<{ [key: string]: AccessibleState }>;
const historyAccessible: AccessibleMapRef = ref({});
const workflowAccessible: AccessibleMapRef = ref({});
const historyDatasetAccessible: AccessibleMapRef = ref({});
function catchErrorToToast(title: string, prolog: string) {
    function handleError(e: Error | MessageException) {
        toast.error(`${prolog} 原因: ${errorMessageAsString(e)}.`, title);
    }
    return handleError;
}

watch(referencedJobIds, async () => {
    referencedJobIds.value.forEach(async (jobId) => {
        if (jobId in jobsToHistories.value) {
            return;
        }

        const handleError = catchErrorToToast(
            "获取作业信息失败",
            "某些引用的对象可能不会被列出。"
        );
        const { data, error } = await GalaxyApi().GET("/api/jobs/{job_id}", {
            params: { path: { job_id: jobId } },
        });

        if (error) {
            handleError(error);
            return;
        }

        if ("history_id" in data) {
            const historyId = data.history_id;
            Vue.set(jobsToHistories.value, jobId, historyId);
        }
    });
});

watch(referencedInvocationIds, async () => {
    referencedInvocationIds.value.forEach(async (invocationId) => {
        if (invocationId in invocationsToHistories.value) {
            return;
        }

        const handleError = catchErrorToToast(
            "获取工作流信息失败",
            "某些引用的对象可能不会被列出。"
        );

        const { data, error } = await GalaxyApi().GET("/api/invocations/{invocation_id}", {
            params: { path: { invocation_id: invocationId } },
        });

        if (error) {
            handleError(error);
            return;
        }

        if ("history_id" in data) {
            const historyId = data.history_id;
            Vue.set(invocationsToHistories.value, invocationId, historyId);
        }
    });
});

watch(referencedHistoryDatasetCollectionIds, async () => {
    referencedHistoryDatasetCollectionIds.value.forEach((historyDatasetCollectionId) => {
        if (historyDatasetCollectionId in historyDatasetCollectionsToHistories.value) {
            return;
        }
        const handleError = catchErrorToToast(
            "获取集合信息失败",
            "某些引用的对象可能不会被列出。"
        );
        fetchCollectionSummary({ id: historyDatasetCollectionId })
            .then((data) => {
                const historyId = data.history_id;
                Vue.set(historyDatasetCollectionsToHistories.value, historyDatasetCollectionId, historyId);
            })
            .catch(handleError);
    });
});

interface ItemInterface {
    id: string;
    accessible: Boolean | null;
    name: string;
    type: string;
}

const histories = computed<ItemInterface[]>(() => {
    return historyIds.value.map((historyId: string) => {
        return {
            id: historyId,
            type: "history",
            name: getHistoryNameById(historyId),
            accessible: historyAccessible.value[historyId],
        } as ItemInterface;
    });
});

const workflows = computed<ItemInterface[]>(() => {
    return referencedWorkflowIds.value.map((workflowId: string) => {
        return {
            id: workflowId,
            type: "workflow",
            name: getStoredWorkflowNameByInstanceId(workflowId),
            accessible: workflowAccessible.value[workflowId],
        } as ItemInterface;
    });
});

const datasets = computed<ItemInterface[]>(() => {
    return referencedHistoryDatasetIds.value.map((historyDatasetId: string) => {
        return {
            id: historyDatasetId,
            type: "historyDataset",
            name: getDataset(historyDatasetId)?.name || "正在获取数据集名称...",
            accessible: historyDatasetAccessible.value[historyDatasetId],
        } as ItemInterface;
    });
});

const loading = ref(false);

const SHARING_FIELD = { key: "accessible", label: _l("可访问性"), sortable: false, thStyle: { width: "10%" } };
const NAME_FIELD = { key: "name", label: _l("名称"), sortable: true };
const TYPE_FIELD = { key: "type", label: _l("类型"), sortable: true, thStyle: { width: "10%" } };

const tableFields = [SHARING_FIELD, TYPE_FIELD, NAME_FIELD];

watch(
    props,
    () => {
        updateReferences(referencedObjects, props.markdownContent);
        initWorkflowData();
        initHistoryDatasetData();
    },
    { immediate: true }
);

watch(historyIds, async () => {
    for (const historyId of historyIds.value) {
        loadHistoryById(historyId);
        if (historyId && !(historyId in historyAccessible.value)) {
            Vue.set(historyAccessible.value, historyId, null);

            const { data, error } = await GalaxyApi().GET("/api/histories/{history_id}/sharing", {
                params: { path: { history_id: historyId } },
            });

            if (error) {
                const errorMessage = errorMessageAsString(error);
                const title = "获取历史记录元数据失败。";
                toast.error(errorMessage, title);
                Vue.set(historyAccessible.value, historyId, `${title} 原因: ${errorMessage}.`);
                return;
            }

            const accessible = data.importable;
            Vue.set(historyAccessible.value, historyId, accessible);
        }
    }
});

async function initWorkflowData() {
    for (const workflowId of referencedWorkflowIds.value) {
        fetchWorkflowForInstanceId(workflowId);
        if (workflowId && !(workflowId in workflowAccessible.value)) {
            Vue.set(workflowAccessible.value, workflowId, null);

            const { data, error } = await GalaxyApi().GET("/api/workflows/{workflow_id}/sharing", {
                params: { path: { workflow_id: workflowId } },
            });

            if (error) {
                const errorMessage = errorMessageAsString(error);
                const title = "获取工作流元数据失败。";
                toast.error(errorMessage, title);
                Vue.set(workflowAccessible.value, workflowId, `${title} 原因: ${errorMessage}.`);
                return;
            }

            const accessible = data.importable;
            Vue.set(workflowAccessible.value, workflowId, accessible);
        }
    }
}

function initHistoryDatasetData() {
    for (const historyDatasetId of referencedHistoryDatasetIds.value) {
        fetchDataset({ id: historyDatasetId });
        if (historyDatasetId && !(historyDatasetId in historyDatasetAccessible.value)) {
            axios
                .get(withPrefix(`/dataset/get_edit?dataset_id=${historyDatasetId}`))
                .then((response) => {
                    const permissionDisable = response.data.permission_disable;
                    const permissionInputs = response.data.permission_inputs;
                    if (permissionDisable) {
                        const errorStr = `无法修改此数据集的权限。原因: ${permissionInputs[0].label}`;
                        Vue.set(historyDatasetAccessible.value, historyDatasetId, errorStr);
                        return;
                    }
                    const accessPermissionInput = permissionInputs[1];
                    if (accessPermissionInput.name != "DATASET_ACCESS") {
                        throw Error("Galaxy Bug");
                    }
                    const accessible = (accessPermissionInput.value || []).length == 0;
                    Vue.set(historyDatasetAccessible.value, historyDatasetId, accessible);
                })
                .catch((e) => {
                    const errorMessage = errorMessageAsString(e);
                    const title = "获取数据集元数据失败。";
                    toast.error(errorMessage, title);
                    Vue.set(historyDatasetAccessible.value, historyDatasetId, `${title} 原因: ${errorMessage}.`);
                });
        }
    }
}

const tableItems = computed<ItemInterface[]>(() => {
    return [...histories.value, ...workflows.value, ...datasets.value];
});

async function makeAccessible(item: ItemInterface) {
    let accessibleResult: Boolean | undefined = undefined;
    let errorResult: MessageException | undefined = undefined;
    let accessibleMap: AccessibleMapRef;
    if (item.type == "history") {
        const { data, error } = await GalaxyApi().PUT("/api/histories/{history_id}/enable_link_access", {
            params: { path: { history_id: item.id } },
        });

        errorResult = error;
        accessibleResult = data?.importable;
        accessibleMap = historyAccessible;
    } else if (item.type == "workflow") {
        const { data, error } = await GalaxyApi().PUT("/api/workflows/{workflow_id}/enable_link_access", {
            params: { path: { workflow_id: item.id } },
        });

        errorResult = error;
        accessibleResult = data?.importable;
        accessibleMap = workflowAccessible;
    } else if (item.type == "historyDataset") {
        const { data, error } = await GalaxyApi().PUT("/api/datasets/{dataset_id}/permissions", {
            params: { path: { dataset_id: item.id } },
            body: {
                action: "remove_restrictions",
            },
        });

        errorResult = error;
        accessibleResult = data !== undefined;
        accessibleMap = historyDatasetAccessible;
    } else {
        console.log("严重的客户端编程错误 - 遇到未知对象类型。");
        return;
    }
    if (errorResult) {
        const errorMessage = errorMessageAsString(errorResult);
        const title = "更新对象可访问性失败。";
        toast.error(errorMessage, title);
        Vue.set(accessibleMap.value, item.id, `${title} 原因: ${errorMessage}.`);
        return;
    }
    Vue.set(accessibleMap.value, item.id, accessibleResult);
}
</script>

<template>
    <div>
        <b-table :items="tableItems" show-empty :fields="tableFields">
            <template v-slot:empty>
                <LoadingSpan v-if="loading" message="加载对象中" />
                <b-alert v-else variant="info" show>
                    <div>在引用的Galaxy markdown内容中未找到对象。</div>
                </b-alert>
            </template>
            <template v-slot:cell(name)="row">
                {{ row.item.name }}
            </template>
            <template v-slot:cell(accessible)="row">
                <SharingIndicator :accessible="row.item.accessible" @makeAccessible="makeAccessible(row.item)" />
            </template>
            <template v-slot:cell(type)="row">
                <PermissionObjectType :type="row.item.type" />
            </template>
        </b-table>
    </div>
</template>
