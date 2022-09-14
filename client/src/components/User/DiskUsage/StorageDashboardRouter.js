import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import VueRouter from "vue-router";
import StorageManager from "./Management/StorageManager";
import StorageDashboard from "./StorageDashboard";

Vue.use(VueRouter);

export default new VueRouter({
    mode: "history",
    base: `${getAppRoot()}storage`,
    routes: [
        {
            path: "/",
            name: "StorageDashboard",
            component: StorageDashboard,
        },
        {
            path: "/management",
            name: "StorageManager",
            component: StorageManager,
            props: true,
        },
        {
            path: "*",
            redirect: { name: "StorageDashboard" },
        },
    ],
});
