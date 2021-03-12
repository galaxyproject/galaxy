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
    base: `${getAppRoot()}libraries`,
    routes: [
        {
            path: "/",
            name: "LibrariesList",
            component: LibrariesList,
        },
        {
            path: "/permissions/:library_id",
            name: "LibraryPermissions",
            component: LibraryPermissions,
        },
        {
            path: "/folders/:folder_id",
            name: "LibraryFolder",
            component: LibraryFolder,
            props: true,
        },
        {
            path: "/folders/permissions/:folder_id",
            name: "LibraryFolder",
            component: LibraryFolderPermissions,
            props: true,
        },
        {
            path: "/folders/permissions/:folder_id/dataset/:dataset_id",
            name: "LibraryFolder",
            component: LibraryFolderDatasetPermissions,
            props: true,
        },
    ],
});
