<script>
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import VueRouter from "vue-router";
import LibraryFolderPermissions from "./LibraryFolderPermissions/LibraryFolderPermissions.vue";
import LibraryFolder from "components/LibraryFolder/LibraryFolder.vue";

Vue.use(VueRouter);

export default new VueRouter({
    mode: "history",
    base: `${getAppRoot()}library/folders`,
    routes: [
        {
            path: "/:folder_id",
            name: "LibraryFolder",
            component: LibraryFolder,
            props: true,
        },
        {
            path: "/permissions/:folder_id",
            name: "LibraryFolder",
            component: LibraryFolderPermissions,
            props: true,
        },
    ],
});
</script>
