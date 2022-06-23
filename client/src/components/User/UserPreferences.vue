<template>
    <b-container fluid class="p-0">
        <h2 v-localize>User preferences</h2>
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <p>
            {{ titleLoggedInAs }} <strong id="user-preferences-current-email">{{ email }}</strong
            >.
        </p>
        <b-row v-for="(link, index) in activeLinks" :key="index" class="ml-3 mb-1">
            <i :class="['pref-icon pt-1 fa fa-lg', link.icon]" />
            <div class="pref-content pr-1">
                <a v-if="link.onclick" :id="link.id" href="javascript:void(0)" @click="link.onclick"
                    ><b>{{ link.title }}</b></a
                >
                <a v-else :id="link.id" :href="`${baseUrl}/${link.action}`"
                    ><b>{{ link.title }}</b></a
                >
                <div class="form-text text-muted">
                    {{ link.description }}
                </div>
            </div>
        </b-row>
        <b-row class="ml-3 mb-1">
            <i class="pref-icon pt-1 fa fa-lg fa-plus-square-o" />
            <div class="pref-content pr-1">
                <a href="javascript:void(0)" @click="toggleNotifications"><b v-localize>Enable notifications</b></a>
                <div v-localize class="form-text text-muted">
                    Allow push and tab notifcations on job completion. To disable, revoke the site notification
                    privilege in your browser.
                </div>
            </div>
        </b-row>
        <ConfigProvider v-slot="{ config }">
            <UserDeletion
                v-if="config && !config.single_user && config.enable_account_interface"
                :email="email"
                :root="root"
                :user-id="userId">
            </UserDeletion>
        </ConfigProvider>
        <p class="mt-2">
            {{ titleYouAreUsing }} <strong>{{ diskUsage }}</strong> {{ titleOfDiskSpace }}
            <span v-html="quotaUsageString"></span>
            {{ titleIsYourUsage }}
            <a href="https://galaxyproject.org/learn/managing-datasets/" target="_blank"
                ><b v-localize>documentation</b></a
            >
            {{ titleForTipsOnHow }}
        </p>
    </b-container>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";
import axios from "axios";
import QueryStringParsing from "utils/query-string-parsing";
import { getUserPreferencesModel } from "components/User/UserPreferencesModel";
import ConfigProvider from "components/providers/ConfigProvider";
import { userLogoutAll } from "layout/menu";
import UserDeletion from "./UserDeletion";

import "@fortawesome/fontawesome-svg-core";

Vue.use(BootstrapVue);

export default {
    components: {
        ConfigProvider,
        UserDeletion,
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
    data() {
        return {
            email: "",
            diskUsage: "",
            quotaUsageString: "",
            root: getAppRoot(),
            messageVariant: null,
            message: null,
            submittedNames: [],
            titleYouAreUsing: _l("You are using"),
            titleOfDiskSpace: _l("of disk space in this Galaxy instance."),
            titleIsYourUsage: _l("Is your usage more than expected? See the"),
            titleForTipsOnHow: _l("for tips on how to find all of the data in your account."),
            titleLoggedInAs: _l("You are logged in as"),
        };
    },
    computed: {
        baseUrl() {
            return `${this.root}user`;
        },
        activeLinks() {
            const activeLinks = {};
            const UserPreferencesModel = getUserPreferencesModel();
            for (const key in UserPreferencesModel) {
                if (UserPreferencesModel[key].shouldRender !== false) {
                    activeLinks[key] = UserPreferencesModel[key];
                    switch (key) {
                        case "make_data_private":
                            activeLinks[key].onclick = this.makeDataPrivate;
                            break;
                        case "custom_builds":
                            activeLinks[key].onclick = this.openManageCustomBuilds;
                            break;
                        case "logout":
                            activeLinks[key].onclick = this.signOut;
                            break;
                        // case "delete_user":
                        //     activeLinks[key].onclick = this.deleteUser;
                        default:
                            activeLinks[key].action = key;
                    }
                }
            }

            return activeLinks;
        },
    },
    created() {
        const message = QueryStringParsing.get("message");
        const status = QueryStringParsing.get("status");
        if (message && status) {
            this.message = message;
            this.messageVariant = status;
        }
        axios.get(`${getAppRoot()}api/users/${this.userId}`).then((response) => {
            this.email = response.data.email;
            this.diskUsage = response.data.nice_total_disk_usage;
            this.quotaUsageString = this.enableQuotas
                ? `Your disk quota is: <strong>${response.data.quota}</strong>.`
                : "";
        });
    },
    methods: {
        toggleNotifications() {
            if (window.Notification) {
                Notification.requestPermission().then(function (permission) {
                    //If the user accepts, let's create a notification
                    if (permission === "granted") {
                        new Notification("Notifications enabled", {
                            icon: "static/favicon.ico",
                        });
                    } else {
                        alert("Notifications disabled, please re-enable through browser settings.");
                    }
                });
            } else {
                alert("Notifications are not supported by this browser.");
            }
        },
        openManageCustomBuilds() {
            const Galaxy = getGalaxyInstance();
            Galaxy.page.router.push(`${getAppRoot()}custom_builds`);
        },
        makeDataPrivate() {
            const Galaxy = getGalaxyInstance();
            if (
                confirm(
                    _l(
                        "WARNING: This will make all datasets (excluding library datasets) for which you have " +
                            "'management' permissions, in all of your histories " +
                            "private, and will set permissions such that all " +
                            "of your new data in these histories is created as private.  Any " +
                            "datasets within that are currently shared will need " +
                            "to be re-shared or published.  Are you sure you " +
                            "want to do this?"
                    )
                )
            ) {
                axios.post(`${getAppRoot()}history/make_private?all_histories=true`).then((response) => {
                    Galaxy.modal.show({
                        title: _l("Datasets are now private"),
                        body: `All of your histories and datsets have been made private.  If you'd like to make all *future* histories private please use the <a href="${Galaxy.root}user/permissions">User Permissions</a> interface.`,
                        buttons: {
                            Close: () => {
                                Galaxy.modal.hide();
                            },
                        },
                    });
                });
            }
        },
        signOut() {
            const Galaxy = getGalaxyInstance();
            Galaxy.modal.show({
                title: _l("Sign out"),
                body: "Do you want to continue and sign out of all active sessions?",
                buttons: {
                    Cancel: function () {
                        Galaxy.modal.hide();
                    },
                    "Sign out": userLogoutAll,
                },
            });
        },
    },
};
</script>
<style scoped>
@import "user-styles.scss";
</style>
