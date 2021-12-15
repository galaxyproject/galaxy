import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import VueRouter from "vue-router";
import LibraryFolderPermissions from "components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryFolderPermissions.vue";
import LibraryDataset from "components/Libraries/LibraryFolder/LibraryFolderDataset/LibraryDataset.vue";
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
        // redirect to the 1st page
        { path: "/folders/:folder_id", redirect: "/folders/:folder_id/page/1" },
        {
            path: "/folders/:folder_id/page/:page",
            name: "LibraryFolder",
            component: LibraryFolder,
            props(route) {
                const props = { ...route.params };
                if (props.page) {
                    props.page = +props.page;
                }
                return props;
            },
        },
        {
            path: "/folders/:folder_id/dataset/:dataset_id",
            name: "LibraryDataset",
            component: LibraryDataset,
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
            name: "LibraryFolderDatasetPermissions",
            component: LibraryFolderDatasetPermissions,
            props: true,
        },
    ],
});
