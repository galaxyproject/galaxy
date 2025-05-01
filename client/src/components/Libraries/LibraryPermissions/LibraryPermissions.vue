<template>
    <div>
        <b-button variant="link" @click="onGoBack">返回文库</b-button>
        <PermissionsHeader v-if="library" :name="library.name" />
        <h1 class="text-center h-lg">文库权限</h1>
        <PermissionsInputField
            v-if="access_library_role_list"
            :id="library_id"
            :permission_type="access_type"
            :initial_value="access_library_role_list"
            :api-root-url="apiRootUrl"
            alert="拥有<strong>任意</strong>这些角色的用户可以访问此文库。如果文库未设置访问角色，则视为<strong>无限制</strong>。"
            title="可以访问文库的角色"
            @input="setUserPermissionsPreferences" />
        <PermissionsInputField
            v-if="add_library_item_role_list"
            :id="library_id"
            :permission_type="add_type"
            :initial_value="add_library_item_role_list"
            :api-root-url="apiRootUrl"
            class="add_perm"
            alert="拥有<strong>任意</strong>这些角色的用户可以向此文库添加项目（文件夹和数据集）。"
            title="可以向此文库添加项目的角色"
            @input="setUserPermissionsPreferences" />
        <PermissionsInputField
            v-if="modify_library_role_list"
            :id="library_id"
            :permission_type="modify_type"
            :initial_value="modify_library_role_list"
            :api-root-url="apiRootUrl"
            alert="拥有<strong>任意</strong>这些角色的用户可以修改此文库（名称、简介等）。"
            title="可以修改此文库的角色"
            @input="setUserPermissionsPreferences" />
        <PermissionsInputField
            v-if="manage_library_role_list"
            :id="library_id"
            :permission_type="manage_type"
            :initial_value="manage_library_role_list"
            :api-root-url="apiRootUrl"
            alert="拥有<strong>任意</strong>这些角色的用户可以管理此文库。"
            title="可以管理此文库的角色"
            @input="setUserPermissionsPreferences" />
        <button title="保存修改" class="toolbtn_save_permissions" @click="postPermissions">
            <FontAwesomeIcon :icon="['far', 'save']" />
            保存
        </button>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import { initPermissionsIcons } from "components/Libraries/icons";
import { extractRoles } from "components/Libraries/library-utils";
import PermissionsHeader from "components/Libraries/LibraryPermissions/PermissionsHeader";
import PermissionsInputField from "components/Libraries/LibraryPermissions/PermissionsInputField";
import { Services } from "components/Libraries/LibraryPermissions/services";
import { Toast } from "composables/toast";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";

Vue.use(BootstrapVue);
initPermissionsIcons();

export default {
    components: {
        PermissionsHeader,
        PermissionsInputField,
        FontAwesomeIcon,
    },
    props: {
        library_id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            permissions: undefined,
            library: undefined,
            add_library_item_role_list: undefined,
            modify_library_role_list: undefined,
            manage_library_role_list: undefined,
            access_library_role_list: undefined,
            apiRootUrl: `${getAppRoot()}api/libraries`,
            add_type: "add_library_item_role_list",
            modify_type: "modify_library_role_list",
            manage_type: "manage_library_role_list",
            access_type: "access_library_role_list",
        };
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.services.getLibraryPermissions(this.library_id).then((fetched_permissions) => {
            console.log("fetched_permissions", fetched_permissions);
            this.add_library_item_role_list = extractRoles(fetched_permissions.add_library_item_role_list);
            this.modify_library_role_list = extractRoles(fetched_permissions.modify_library_role_list);
            this.manage_library_role_list = extractRoles(fetched_permissions.manage_library_role_list);
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
                this.library_id,
                [
                    { "add_ids[]": this.add_library_item_role_list },
                    { "modify_ids[]": this.modify_library_role_list },
                    { "manage_ids[]": this.manage_library_role_list },
                    { "access_ids[]": this.access_library_role_list },
                ],
                (fetched_permissions) => {
                    Toast.success("文库权限已保存。");
                    this.permissions = fetched_permissions;
                },
                (error) => {
                    Toast.error("尝试设置文件夹权限时发生错误。");
                    console.error(error);
                }
            );
        },
        onGoBack() {
            this.$router.go(-1);
        },
    },
};
</script>
