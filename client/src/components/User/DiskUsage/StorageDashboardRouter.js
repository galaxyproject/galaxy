import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import VueRouter from "vue-router";
import StorageDashboard from "./StorageDashboard";

Vue.use(VueRouter);

export default new VueRouter({
    mode: "history",
    base: `${getAppRoot()}storage`,
    routes: [
        {
            path: "/",
            name: "Dashboard",
            component: StorageDashboard,
        },
        {
            path: "*",
            redirect: { name: "Dashboard" },
        },
    ],
});
