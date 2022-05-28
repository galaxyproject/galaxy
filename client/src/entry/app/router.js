import Vue from "vue";
import VueRouter from "vue-router";

import Analysis from "entry/app/modules/Analysis.vue";
import WorkflowEditorModule from "entry/app/modules/WorkflowEditor.vue";

Vue.use(VueRouter);

const router = new VueRouter({
    routes: [
        { path: "/home", component: Analysis },
        { path: "/workflows/edit", component: WorkflowEditorModule },
    ],
});

export default router;
