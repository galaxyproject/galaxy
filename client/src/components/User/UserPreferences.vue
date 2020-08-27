<template>
    <b-container fluid class="p-0">
        <h2>User preferences</h2>
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <p>
            You are logged in as <strong id="user-preferences-current-email">{{ email }}</strong
            >.
        </p>
        <b-row class="ml-3 mb-1" v-for="(link, index) in activeLinks" :key="index">
            <i :class="['pref-icon pt-1 fa fa-lg', link.icon]" />
            <div class="pref-content pr-1">
                <a :id="link.id" v-if="link.onclick" @click="link.onclick" href="javascript:void(0)"
                    ><b>{{ link.title }}</b></a
                >
                <a :id="link.id" v-else :href="`${baseUrl}/${link.action}`"
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
                <a @click="toggleNotifications" href="javascript:void(0)"><b>Enable notifications</b></a>
                <div class="form-text text-muted">
                    Allow push and tab notifcations on job completion. To disable, revoke the site notification
                    privilege in your browser.
                </div>
            </div>
        </b-row>
        <p class="mt-2">
            You are using <strong>{{ diskUsage }}</strong> of disk space in this Galaxy instance.
            <span v-html="quotaUsageString"></span>
            Is your usage more than expected? See the
            <a href="https://galaxyproject.org/learn/managing-datasets/" target="_blank"><b>documentation</b></a> for
            tips on how to find all of the data in your account.
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

Vue.use(BootstrapVue);

export default {
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
            baseUrl: `${getAppRoot()}user`,
            messageVariant: null,
            message: null,
        };
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
    computed: {
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
                        default:
                            activeLinks[key].action = key;
                    }
                }
            }

            return activeLinks;
        },
    },
    methods: {
        toggleNotifications() {
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
                    "Sign out": function () {
                        window.location.href = `${getAppRoot()}user/logout?session_csrf_token=${
                            Galaxy.session_csrf_token
                        }`;
                    },
                },
            });
        },
    },
};
</script>

<style scoped>
.pref-content {
    width: calc(100% - 3rem);
}
.pref-icon {
    width: 3rem;
}
</style>
