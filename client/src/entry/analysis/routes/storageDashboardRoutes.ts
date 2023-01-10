import StorageManager from "@/components/User/DiskUsage/Management/StorageManager.vue";
import StorageDashboard from "@/components/User/DiskUsage/StorageDashboard.vue";
import Base from "@/entry/analysis/modules/Base.vue";

export default [
    {
        path: "/storage",
        component: Base,
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
                path: "*",
                redirect: { name: "StorageDashboard" },
            },
        ],
    },
];
