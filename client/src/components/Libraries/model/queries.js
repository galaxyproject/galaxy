import axios from "axios";
import { prependPath } from "utils/redirect";
import { Library } from "./Library";

const api = axios.create({
    baseURL: prependPath("/api"),
});

/**
 * Libraries
 */

export async function getLibraries(params) {
    const response = await api.get(`/libraries?${params.searchQuery}`);
    return response.data.map(Library.create);
}

export async function getLibraryById(id) {
    const response = await api.get(`/libraries/${id}`);
    return Library.create(response.data);
}

export async function createLibrary(lib = {}) {
    console.log("createLibrary");
}

export async function saveLibrary(lib = {}) {
    console.log("saveLibrary");
}

export async function deleteLibrary(lib = {}) {
    console.log("deleteLibrary");
}

/**
 * Library folder contents
 */

export async function getFolderContents(params) {
    console.log("getFolderContents", params);
}

// await this.saveLibrary({ deleted: true });
//     console.log("deleteLibrary", arguments);
//     const url = prependPath(`libraries/${this.folderId}${isUndelete ? "?undelete=true" : ""}`);
//     const response = await fetch(url, {
//         method: "DELETE",
//         credentials: "include",
//     });
// },
// async deleteLibrary(lib, onSucess, onError, isUndelete = false) {
//     const url = prependPath(`api/libraries/${lib.id}${isUndelete ? "?undelete=true" : ""}`);
//     try {
//         const response = axios
//             .delete(url, lib)
//             .then((response) => {
//                 onSucess(response.data);
//             })
//             .catch((error) => {
//                 onError(error);
//             });
//         return response.data;
//     } catch (e) {
//         rethrowSimple(e);
//     }
// },

// async createNewLibrary(name, description, synopsis, onSucess, onError) {
//     const url = prependPath(`api/libraries/`);
//     try {
//         const response = axios
//             .post(url, {
//                 name: name,
//                 description: description,
//                 synopsis: synopsis,
//             })
//             .then((response) => {
//                 onSucess(response.data);
//             })
//             .catch((error) => {
//                 onError(error);
//             });
//         return response.data;
//     } catch (e) {
//         rethrowSimple(e);
//     }
// },

// import { getAppRoot } from "onload/loadConfig";
// import { Services } from "./services";
// import { fields } from "./table-fields";
// import { Toast } from "ui/toast";
// import { initLibariesIcons } from "components/Libraries/icons";
// import { MAX_DESCRIPTION_LENGTH, DEFAULT_PER_PAGE, onError } from "components/Libraries/library-utils";
// import LibraryEditField from "components/Libraries/LibraryEditField";
// import SearchField from "components/Libraries/LibraryFolder/SearchField";
// import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
// initLibariesIcons();

// async fetchFolderContents(include_deleted = false) {
//     this.include_deleted = include_deleted;
//     this.setBusy(true);
//     this.services
//         .getFolderContents(
//             this.current_folder_id,
//             include_deleted,
//             this.perPage,
//             (this.currentPage - 1) * this.perPage,
//             this.search_text
//         )
//         .then((response) => {
//             this.folderContents = response.folder_contents;
//             this.folder_metadata = response.metadata;
//             this.total_rows = response.metadata.total_rows;
//             if (this.isAllSelectedMode) {
//                 this.selected = [];
//                 this.$nextTick(() => {
//                     this.selectAllRenderedRows();
//                 });
//             } else if (this.selected.length > 0) {
//                 this.$nextTick(() => {
//                     this.selected.forEach((row) => this.select_unselect_row_by_id(row.id));
//                 });
//             }
//             this.setBusy(false);
//         })
//         .catch((error) => {
//             this.error = error;
//         });
// },
