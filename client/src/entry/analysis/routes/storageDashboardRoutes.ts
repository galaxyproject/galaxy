import StorageManager from "@/components/User/DiskUsage/Management/StorageManager.vue";
import StorageDashboard from "@/components/User/DiskUsage/StorageDashboard.vue";
import HistoriesStorageOverview from "@/components/User/DiskUsage/Visualizations/HistoriesStorageOverview.vue";
import HistoryStorageOverview from "@/components/User/DiskUsage/Visualizations/HistoryStorageOverview.vue";
import Base from "@/entry/analysis/modules/Base.vue";

export default [
    {
        path: "/storage",
        component: Base,
        meta: { requiresRegisteredUser: true },
        children: [
            {
                path: "",
                name: "StorageDashboard",
                component: StorageDashboard,
            },
            {
                path: "management",
                name: "StorageManager",
                component: StorageManager,
                props: true,
            },
            {
                path: "histories",
                name: "HistoriesOverview",
                component: HistoriesStorageOverview,
            },
            {
                path: "history/:historyId",
                name: "HistoryOverview",
                component: HistoryStorageOverview,
                props: true,
            },
            {
                path: "*",
                redirect: { name: "StorageDashboard" },
            },
        ],
    },
];
