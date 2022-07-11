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
            <b-row v-if="config && !config.single_user && config.enable_account_interface" class="ml-3 mb-1">
                <i class="pref-icon pt-1 fa fa-lg fa-radiation" />
                <div class="pref-content pr-1">
                    <a id="delete-account" href="javascript:void(0)"
                        ><b v-b-modal.modal-prevent-closing v-localize>Delete Account</b></a
                    >
                    <div v-localize class="form-text text-muted">Delete your account on this Galaxy server.</div>
                    <b-modal
                        id="modal-prevent-closing"
                        ref="modal"
                        centered
                        title="Account Deletion"
                        title-tag="h2"
                        @show="resetModal"
                        @hidden="resetModal"
                        @ok="handleOk">
                        <p>
                            <b-alert variant="danger" :show="showDeleteError">{{ deleteError }}</b-alert>
                            <b>
                                This action cannot be undone. Your account will be permanently deleted, along with the
                                data contained in it.
                            </b>
                        </p>
                        <b-form ref="form" @submit.prevent="handleSubmit">
                            <b-form-group
                                :state="nameState"
                                label="Enter your user email for this account as confirmation."
                                label-for="Email"
                                invalid-feedback="Incorrect email">
                                <b-form-input id="name-input" v-model="name" :state="nameState" required></b-form-input>
                            </b-form-group>
                        </b-form>
                    </b-modal>
                </div>
            </b-row>
        </ConfigProvider>
        <p class="mt-2">
            You are using <strong>{{ diskUsage }}</strong> of disk space in this Galaxy instance.
            <span v-if="enableQuotas">
                Your disk quota is: <strong>{{ diskQuota }}</strong
                >.
            </span>
            Is your usage more than expected? Review your
            <b-link :href="storageDashboardUrl"><b>Storage Dashboard</b></b-link
            >.
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
import { userLogoutAll, userLogoutClient } from "layout/menu";
import "@fortawesome/fontawesome-svg-core";

Vue.use(BootstrapVue);

export default {
    components: {
        ConfigProvider,
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
            diskQuota: "",
            storageDashboardUrl: `${getAppRoot()}storage`,
            baseUrl: `${getAppRoot()}user`,
            messageVariant: null,
            message: null,
            name: "",
            nameState: null,
            deleteError: "",
            submittedNames: [],
            titleLoggedInAs: _l("You are logged in as"),
        };
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
                        // case "delete_user":
                        //     activeLinks[key].onclick = this.deleteUser;
                        default:
                            activeLinks[key].action = key;
                    }
                }
            }

            return activeLinks;
        },
        showDeleteError() {
            return this.deleteError !== "";
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
            this.diskQuota = response.data.quota;
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
        checkFormValidity() {
            const valid = this.$refs.form.checkValidity();
            this.nameState = valid;
            return valid;
        },
        resetModal() {
            this.name = "";
            this.nameState = null;
        },
        handleOk(bvModalEvt) {
            // Prevent modal from closing
            bvModalEvt.preventDefault();
            // Trigger submit handler
            this.handleSubmit();
        },
        async handleSubmit() {
            if (!this.checkFormValidity()) {
                return false;
            }
            if (this.email === this.name) {
                this.nameState = true;
                try {
                    await axios.delete(`${getAppRoot()}api/users/${this.userId}`);
                } catch (e) {
                    if (e.response.status === 403) {
                        this.deleteError =
                            "User deletion must be configured on this instance in order to allow user self-deletion.  Please contact an administrator for assistance.";
                        return false;
                    }
                }
                userLogoutClient();
            } else {
                this.nameState = false;
                return false;
            }
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
