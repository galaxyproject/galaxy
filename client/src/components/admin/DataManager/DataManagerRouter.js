import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import VueRouter from "vue-router";
import DataManager from "./DataManager";
import DataManagerJobs from "./DataManagerJobs";
import DataManagerJob from "./DataManagerJob";
import DataManagerTable from "./DataManagerTable";

Vue.use(VueRouter);

export default new VueRouter({
    mode: "history",
    base: `${getAppRoot()}admin/data_manager`,
    routes: [
        {
            path: "/",
            name: "DataManager",
            component: DataManager,
        },
        {
            path: "/jobs/:id",
            name: "DataManagerJobs",
            component: DataManagerJobs,
            props: true,
        },
        {
            path: "/job/:id",
            name: "DataManagerJob",
            component: DataManagerJob,
            props: true,
        },
        {
            path: "/table/:name",
            name: "DataManagerTable",
            component: DataManagerTable,
            props: true,
        },
        {
            path: "*",
            redirect: "/",
        },
    ],
});
