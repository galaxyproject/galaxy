<script>
import Vue from "vue";
import VueRouter from "vue-router";
import DataManager from "./DataManager.vue";
import DataManagerJobs from "./DataManagerJobs.vue";
import DataManagerJob from "./DataManagerJob.vue";
import DataManagerTable from "./DataManagerTable.vue";

Vue.use(VueRouter);

export default new VueRouter({
    base: `${Galaxy.root}admin/data_manager`,
    routes: [
        {
            path: "/",
            name: "DataManager",
            component: DataManager
        },
        {
            path: "/jobs/:id",
            name: "DataManagerJobs",
            component: DataManagerJobs,
            props: true
        },
        {
            path: "/job/:id",
            name: "DataManagerJob",
            component: DataManagerJob,
            props: true
        },
        {
            path: "/table/:name",
            name: "DataManagerTable",
            component: DataManagerTable,
            props: true
        }
    ]
});
</script>
