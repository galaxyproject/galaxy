import Vue from "vue";
import VueRouter from "vue-router";
import WorkflowEditorModule from "entry/app/modules/WorkflowEditor.vue";

Vue.use(VueRouter);

const router = new VueRouter({
    routes: [
        { path: "/workflows/edit", component: WorkflowEditorModule },
    ],
});

export default router;
