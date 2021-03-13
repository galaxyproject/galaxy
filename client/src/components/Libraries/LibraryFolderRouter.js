import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import VueRouter from "vue-router";
import LibraryFolderPermissions from "components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryFolderPermissions.vue";
import LibraryFolder from "components/Libraries/LibraryFolder/LibraryFolder.vue";
import LibraryFolderDatasetPermissions from "components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryFolderDatasetPermissions.vue";
import LibrariesList from "components/Libraries/LibrariesList.vue";

Vue.use(VueRouter);

export default new VueRouter({
    mode: "history",
    base: `${getAppRoot()}library`,
    routes: [
        {
            path: "/libraries-list",
            name: "LibrariesList",
            component: LibrariesList,
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
