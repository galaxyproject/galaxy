import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import VueRouter from "vue-router";
import LibraryFolderPermissions from "components/LibraryFolder/LibraryFolderPermissions/LibraryFolderPermissions";
import LibraryFolder from "components/LibraryFolder/LibraryFolder";
import LibraryFolderDatasetPermissions from "components/LibraryFolder/LibraryFolderPermissions/LibraryFolderDatasetPermissions";

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
        {
            path: "/permissions/:folder_id/dataset/:dataset_id",
            name: "LibraryFolder",
            component: LibraryFolderDatasetPermissions,
            props: true,
        },
    ],
});
