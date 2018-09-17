<script>
import Vue from "vue";
import VueRouter from "vue-router";
import DataManager from "./DataManager.vue";

Vue.use(VueRouter);

export default new VueRouter({
    base: `${Galaxy.root}admin/data_manager`,
    routes: [
        {
            path: "/",
            name: "DataManager",
            component: DataManager
        }
    ]
});
</script>
