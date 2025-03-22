<template>
    <b-container fluid class="p-0">
        <h1 v-localize class="h-lg">用户偏好设置</h1>
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <p>
            <span v-localize>您已登录为</span>
            <strong id="user-preferences-current-email">{{ email }}</strong>
            <span v-localize>并且您正在使用</span>
            <strong>{{ diskUsage }}</strong>
            <span v-localize>的磁盘空间。</span>
            <span v-localize>如果使用量超出预期，请访问</span>
            <router-link id="edit-preferences-cloud-auth" to="/storage">
                <b v-localize>存储控制面板</b>
            </router-link>
            <span v-localize>以释放磁盘空间。</span>
            <span v-if="enableQuotas">
                <span v-localize>您的磁盘配额是：</span>
                <strong>{{ diskQuota }}</strong
                >.
            </span>
        </p>
        <UserPreferencesElement
            v-for="(link, index) in activePreferences"
            :id="link.id"
            :key="index"
            :icon="link.icon"
            :title="link.title"
            :description="link.description"
            :to="`/user/${index}`" />
        <UserPreferencesElement
            v-if="isConfigLoaded && !config.single_user"
            id="edit-preferences-permissions"
            icon="fa-users"
            title="设置新历史记录的数据集权限"
            description="为新创建的历史记录授予他人默认访问权限。这里所做的更改只会影响在存储这些设置后创建的历史记录。"
            to="/user/permissions" />
        <UserPreferencesElement
            id="edit-preferences-api-key"
            icon="fa-key"
            title="管理API密钥"
            description="访问您当前的API密钥或创建一个新的密钥。"
            to="/user/api_key" />
        <UserPreferencesElement
            id="edit-preferences-notifications"
            icon="fa-bell"
            title="管理通知"
            description="管理您的通知设置。"
            to="/user/notifications/preferences" />
        <UserPreferencesElement
            v-if="isConfigLoaded && config.enable_oidc && !config.fixed_delegated_auth"
            id="manage-third-party-identities"
            icon="fa-id-card-o"
            title="管理第三方身份"
            description="连接或断开与第三方身份的访问。"
            to="/user/external_ids" />
        <UserPreferencesElement
            id="edit-preferences-custom-builds"
            icon="fa-cubes"
            title="管理自定义构建"
            description="使用历史数据集添加或移除自定义构建。"
            to="/custom_builds" />
        <UserPreferencesElement
            v-if="hasThemes"
            icon="fa-palette"
            title="选择颜色主题"
            description="点击此处更改用户界面颜色主题。"
            @click="toggleTheme = !toggleTheme">
            <b-collapse v-model="toggleTheme">
                <ThemeSelector />
            </b-collapse>
        </UserPreferencesElement>
        <UserPreferencesElement
            v-if="isConfigLoaded && !config.single_user"
            id="edit-preferences-make-data-private"
            icon="fa-lock"
            title="将所有数据设为私有"
            description="点击此处将所有数据设为私有。"
            @click="makeDataPrivate" />
        <UserBeaconSettings v-if="isConfigLoaded && config.enable_beacon_integration" :user-id="userId">
        </UserBeaconSettings>
        <UserPreferredObjectStore
            v-if="isConfigLoaded && config.object_store_allows_id_selection && currentUser"
            :preferred-object-store-id="currentUser.preferred_object_store_id"
            :user-id="userId">
        </UserPreferredObjectStore>
        <UserPreferencesElement
            v-if="hasObjectStoreTemplates"
            id="manage-object-stores"
            class="manage-object-stores"
            icon="fa-hdd"
            title="管理您的存储位置"
            description="添加、删除或更新您个人配置的存储位置。"
            to="/object_store_instances/index" />
        <UserPreferencesElement
            v-if="hasFileSourceTemplates"
            id="manage-file-sources"
            class="manage-file-sources"
            icon="fa-file"
            title="管理您的远程文件源"
            description="添加、删除或更新您个人配置的查找文件和写入文件的位置。"
            to="/file_source_instances/index" />
        <UserDeletion
            v-if="isConfigLoaded && !config.single_user && config.enable_account_interface"
            :email="email"
            :user-id="userId">
        </UserDeletion>
        <UserPreferencesElement
            v-if="hasLogout"
            id="edit-preferences-sign-out"
            icon="fa-sign-out"
            title="退出登录"
            description="点击此处退出所有会话。"
            @click="showLogoutModal = true" />
        <b-modal v-model="showDataPrivateModal" title="数据集现已设为私有" title-class="font-weight-bold" ok-only>
            <span v-localize>
                您所有的历史记录和数据集已被设为私有。如果您希望将所有*未来*的历史记录设为私有，请使用
            </span>
            <a :href="userPermissionsUrl">用户权限</a>
            <span v-localize>界面</span>.
        </b-modal>
        <b-modal
            v-model="showLogoutModal"
            title="退出登录"
            title-class="font-weight-bold"
            ok-title="退出登录"
            @ok="signOut">
            <span v-localize> 您确定要继续并退出所有活动会话吗？ </span>
        </b-modal>
    </b-container>
</template>

<script>
// 脚本部分保持不变
import { getGalaxyInstance } from "app";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import { getUserPreferencesModel } from "components/User/UserPreferencesModel";
import { mapActions, mapState } from "pinia";
import _l from "utils/localization";
import { userLogoutAll } from "utils/logout";
import QueryStringParsing from "utils/query-string-parsing";
import { withPrefix } from "utils/redirect";
import Vue from "vue";

import { useConfig } from "@/composables/config";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import { useUserStore } from "@/stores/userStore";

import UserBeaconSettings from "./UserBeaconSettings";
import UserDeletion from "./UserDeletion";
import UserPreferencesElement from "./UserPreferencesElement";
import UserPreferredObjectStore from "./UserPreferredObjectStore";

import ThemeSelector from "./ThemeSelector.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        UserDeletion,
        UserPreferencesElement,
        ThemeSelector,
        UserBeaconSettings,
        UserPreferredObjectStore,
    },
    props: {
        userId: {
            type: String,
            required: true,
        },
        enableQuotas: {
            type: Boolean,
            required: true,
        },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    data() {
        return {
            email: "",
            diskUsage: "",
            diskQuota: "",
            messageVariant: null,
            message: null,
            showLogoutModal: false,
            showDataPrivateModal: false,
            toggleTheme: false,
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useObjectStoreTemplatesStore, {
            hasObjectStoreTemplates: "hasTemplates",
        }),
        ...mapState(useFileSourceTemplatesStore, {
            hasFileSourceTemplates: "hasTemplates",
        }),
        activePreferences() {
            const userPreferencesEntries = Object.entries(getUserPreferencesModel());
            // Object.entries returns an array of arrays, where the first element
            // is the key (string) and the second is the value (object)
            const enabledPreferences = userPreferencesEntries.filter((f) => !f[1].disabled);
            return Object.fromEntries(enabledPreferences);
        },
        hasLogout() {
            if (this.isConfigLoaded) {
                const Galaxy = getGalaxyInstance();
                return !!Galaxy.session_csrf_token && !this.config.single_user;
            } else {
                return false;
            }
        },
        hasThemes() {
            if (this.isConfigLoaded) {
                const themes = Object.keys(this.config.themes);
                return themes?.length > 1 ?? false;
            } else {
                return false;
            }
        },
        userPermissionsUrl() {
            return withPrefix("/user/permissions");
        },
    },
    created() {
        const message = QueryStringParsing.get("message");
        const status = QueryStringParsing.get("status");
        if (message && status) {
            this.message = message;
            this.messageVariant = status;
        }
        axios.get(withPrefix(`/api/users/${this.userId}`)).then((response) => {
            this.email = response.data.email;
            this.diskUsage = response.data.nice_total_disk_usage;
            this.diskQuota = response.data.quota;
        });
        this.ensureObjectStoreTemplates();
        this.ensureFileSourceTemplates();
    },
    methods: {
        ...mapActions(useObjectStoreTemplatesStore, {
            ensureObjectStoreTemplates: "ensureTemplates",
        }),
        ...mapActions(useFileSourceTemplatesStore, {
            ensureFileSourceTemplates: "ensureTemplates",
        }),
        toggleNotifications() {
            if (window.Notification) {
                Notification.requestPermission().then(function (permission) {
                    //If the user accepts, let's create a notification
                    if (permission === "granted") {
                        new Notification("通知已启用", {
                            icon: "static/favicon.ico",
                        });
                    } else {
                        alert("通知已禁用，请通过浏览器设置重新启用。");
                    }
                });
            } else {
                alert("此浏览器不支持通知功能。");
            }
        },
        makeDataPrivate() {
            if (
                confirm(
                    _l(
                        "警告：这将使您在所有历史记录（包括已归档和已清除的）中具有\"管理\"权限的所有数据集（不包括库数据集）变为私有，并将设置权限，使得在这些历史记录中创建的所有新数据都设为私有。任何当前共享的数据集都需要重新共享或发布。您确定要这样做吗？"
                    )
                )
            ) {
                axios.post(withPrefix(`/history/make_private?all_histories=true`)).then(() => {
                    this.showDataPrivateModal = true;
                });
            }
        },
        signOut() {
            userLogoutAll();
        },
    },
};
</script>
