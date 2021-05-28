import { prependPath } from "utils/redirect";
import Vue from "vue";
import VueRouter from "vue-router";
import LibraryList from "./LibraryList";
import Library from "./Library";
import FolderContents from "./FolderContents";
import Permissions from "./Permissions";
import FolderPermissions from "./FolderPermissions";
import DatasetPermissions from "./DatasetPermissions";

Vue.use(VueRouter);

export default new VueRouter({
    mode: "history",
    base: prependPath("libraries"),
    routes: [
        {
            name: "LibraryList",
            path: "/",
            component: LibraryList,
        },
        {
            name: "Library",
            path: "/:libraryId",
            component: Library,
            props: true,
            children: [
                {
                    name: "Permissions",
                    path: "/permissions",
                    component: Permissions,
                    props: true,
                },
                {
                    name: "DatasetPermissions",
                    path: "/contents/:folderIds*/dataset/:datasetId",
                    component: DatasetPermissions,
                    props: true,
                },
                {
                    name: "FolderPermissions",
                    path: "/contents/:folderIds*/permissions",
                    component: FolderPermissions,
                    props: true,
                },
                {
                    name: "FolderContents",
                    path: "/contents/:folderIds*",
                    component: FolderContents,
                    props: true,
                },
            ],
        },
    ],
});
