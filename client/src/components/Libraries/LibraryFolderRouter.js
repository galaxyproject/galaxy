import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import VueRouter from "vue-router";
import LibraryFolderPermissions from "components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryFolderPermissions.vue";
import LibraryFolder from "components/Libraries/LibraryFolder/LibraryFolder.vue";
import LibraryFolderDatasetPermissions from "components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryFolderDatasetPermissions.vue";
import LibrariesList from "components/Libraries/LibrariesList.vue";
import LibraryPermissions from "components/Libraries/LibraryPermissions/LibraryPermissions.vue";

Vue.use(VueRouter);

export default new VueRouter({
    mode: "history",
    base: `${getAppRoot()}libraries`,
    routes: [
        {
            path: "/",
            name: "LibrariesList",
            component: LibrariesList,
        },
        {
            path: "/:library_id/permissions",
            name: "LibraryPermissions",
            component: LibraryPermissions,
            props: true,
        },
        {
            path: "/folders/:folder_id",
            name: "LibraryFolder",
            component: LibraryFolder,
            props: true,
        },
        {
            path: "/folders/:folder_id/permissions",
            name: "LibraryFolder",
            component: LibraryFolderPermissions,
            props: true,
        },
        {
            path: "/folders/:folder_id/dataset/:dataset_id/permissions",
            name: "LibraryFolder",
            component: LibraryFolderDatasetPermissions,
            props: true,
        },
    ],
});
