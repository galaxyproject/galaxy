import { computed, type Ref, toRef } from "vue";

import { useHistoryStore } from "@/stores/historyStore";

interface Props {
    historyId: string;
}

export function useHistoryBreadCrumbsToForProps<T extends Props>(props: T, historyAction: string) {
    const historyId = toRef(props, "historyId");
    return useHistoryBreadCrumbsTo(historyId, historyAction);
}

export function useHistoryBreadCrumbsTo(historyId: Ref<string>, historyAction: string) {
    const historyStore = useHistoryStore();

    const breadcrumbItems = computed(() => [
        { title: "Histories", to: "/histories/list" },
        {
            title: historyStore.getHistoryNameById(historyId.value),
            to: `/histories/view?id=${historyId.value}`,
            superText: historyStore.currentHistoryId === historyId.value ? "current" : undefined,
        },
        { title: historyAction },
    ]);
    return {
        breadcrumbItems,
    };
}
