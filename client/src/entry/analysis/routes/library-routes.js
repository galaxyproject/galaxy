import LibrariesList from "@/components/Libraries/LibrariesList.vue";
import LibraryFolder from "@/components/Libraries/LibraryFolder/LibraryFolder.vue";
import LibraryDataset from "@/components/Libraries/LibraryFolder/LibraryFolderDataset/LibraryDataset.vue";
import LibraryFolderDatasetPermissions from "@/components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryFolderDatasetPermissions.vue";
import LibraryFolderPermissions from "@/components/Libraries/LibraryFolder/LibraryFolderPermissions/LibraryFolderPermissions.vue";
import LibraryPermissions from "@/components/Libraries/LibraryPermissions/LibraryPermissions.vue";
import Base from "@/entry/analysis/modules/Base.vue";

export default [
    {
        path: "/libraries",
        component: Base,
        children: [
            { path: "", component: LibrariesList },
            {
                path: ":library_id/permissions",
                name: "LibraryPermissions",
                component: LibraryPermissions,
                props: true,
            },
            { path: "folders/:folder_id", redirect: "folders/:folder_id/page/1" },
            {
                path: "folders/:folder_id/page/:page",
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
                path: "folders/:folder_id/dataset/:dataset_id",
                name: "LibraryDataset",
                component: LibraryDataset,
                props: true,
            },
            {
                path: "folders/:folder_id/permissions",
                name: "LibraryFolderPermissions",
                component: LibraryFolderPermissions,
                props: true,
            },
            {
                path: "folders/:folder_id/dataset/:dataset_id/permissions",
                name: "LibraryFolderDatasetPermissions",
                component: LibraryFolderDatasetPermissions,
                props: true,
            },
        ],
    },
];
