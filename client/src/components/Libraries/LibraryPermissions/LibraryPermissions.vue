<template>
    <div>
        <PermissionsHeader v-if="library" :name="library.name" path="/" />
        <h2 class="text-center">Library permissions</h2>
    </div>
</template>

<script>
import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services";
import { Toast } from "ui/toast";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getGalaxyInstance } from "app";
import PermissionsHeader from "components/Libraries/LibraryPermissions/PermissionsHeader";
import { extractRoles } from "components/Libraries/library-utils";
import { initPermissionsIcons } from "components/Libraries/icons";

Vue.use(BootstrapVue);
initPermissionsIcons();

export default {
    props: {
        library_id: {
            type: String,
            required: true,
        },
    },
    components: {
        PermissionsHeader,
        FontAwesomeIcon,
    },
    data() {
        return {
            permissions: undefined,
            library: undefined,
            add_library_item_role_list: undefined,
            modify_library_role_list: undefined,
            manage_library_role_list: undefined,
            access_library_role_list: undefined,
            add_type: "add_library_item_role_list",
            manage_type: "manage_folder_role_list",
            modify_type: "modify_folder_role_list",
        };
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.services.getLibraryPermissions(this.library_id).then((fetched_permissions) => {
            console.log("fetched_permissions", fetched_permissions);
            this.add_library_item_role_list = extractRoles(fetched_permissions.add_library_item_role_list);
            this.manage_library_role_list = extractRoles(fetched_permissions.manage_library_role_list);
            this.modify_library_role_list = extractRoles(fetched_permissions.modify_library_role_list);
            this.access_library_role_list = extractRoles(fetched_permissions.access_library_role_list);
        });
        this.services.getLibrary(this.library_id).then((library) => {
            this.library = library;
        });
    },

    methods: {
        setUserPermissionsPreferences(ids, permission_type) {
            this[permission_type] = ids;
        },
        postPermissions() {
            this.services.setPermissions(
                this.apiRootUrl,
                this.folder_id,
                [
                    { "add_ids[]": this.add_library_item_role_list },
                    { "manage_ids[]": this.manage_folder_role_list },
                    { "modify_ids[]": this.modify_folder_role_list },
                ],
                (fetched_permissions) => {
                    Toast.success("Permissions saved.");
                    this.permissions = fetched_permissions;
                },
                (error) => {
                    Toast.error("An error occurred while attempting to set folder permissions.");
                    console.error(error);
                }
            );
        },
    },
};
</script>

<style scoped>
.header {
    font-size: 45px;
}
</style>
