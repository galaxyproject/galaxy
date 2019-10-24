<template>
    <b-container fluid class="p-0">
        <h2>User preferences</h2>
        <p>
            You are logged in as <strong>{{ email }}</strong
            >.
        </p>
        <b-row class="ml-3 mb-1" v-for="(link, index) in activeLinks" :key="index">
            <i :class="`pref-icon pt-1 fa fa-lg ${link.icon}`"></i>
            <div class="pref-content pr-1">
                <div>
                    <a v-if="link.onclick" @click="link.onclick" href="javascript:void(0)"
                        ><b>{{ link.title }}</b></a
                    >
                    <a v-else :href="`${baseUrl}/${link.action}`"
                        ><b>{{ link.title }}</b></a
                    >
                </div>
                <div class="form-text text-muted">
                    {{ link.description }}
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
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";
import axios from "axios";
import Ui from "mvc/ui/ui-misc";
import QueryStringParsing from "utils/query-string-parsing";
import { getUserPreferencesModel } from "components/User/UserPreferencesModel";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import $ from "jquery";

Vue.use(BootstrapVue);

export default {
    data() {
        const Galaxy = getGalaxyInstance();
        return {
            user: Galaxy.user,
            email: "",
            diskUsage: "",
            quotaUsageString: "",
            baseUrl: `${getAppRoot()}user`
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        const config = Galaxy.config;
        const message = QueryStringParsing.get("message");
        const status = QueryStringParsing.get("status");

        if (message && status) {
            $(this.$el).prepend(new Ui.Message({ message: message, status: status }).$el);
        }

        axios.get(`${getAppRoot()}api/users/${Galaxy.user.id}`).then(response => {
            this.email = response.data.email;
            this.diskUsage = response.data.nice_total_disk_usage;
            this.quotaUsageString = config.enable_quotas
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
                            activeLinks[key]["onclick"] = this.makeDataPrivate;
                            break;
                        case "custom_builds":
                            activeLinks[key]["onclick"] = this.openManageCustomBuilds;
                            break;
                        case "genomespace":
                            activeLinks[key]["onclick"] = this.requestGenomeSpace;
                            break;
                        case "logout":
                            activeLinks[key]["onclick"] = this.signOut;
                            break;
                        default:
                            activeLinks[key]["action"] = key;
                    }
                }
            }

            return activeLinks;
        }
    },
    methods: {
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
                $.post(`${Galaxy.root}history/make_private`, { all_histories: true }, () => {
                    Galaxy.modal.show({
                        title: _l("Datasets are now private"),
                        body: `All of your histories and datsets have been made private.  If you'd like to make all *future* histories private please use the <a href="${
                            Galaxy.root
                        }user/permissions">User Permissions</a> interface.`,
                        buttons: {
                            Close: function() {
                                Galaxy.modal.hide();
                            }
                        }
                    });
                });
            }
        },
        requestGenomeSpace() {
            window.location.href = `${getAppRoot()}openid/openid_auth?openid_provider=genomespace`;
        },
        signOut() {
            const Galaxy = getGalaxyInstance();
            Galaxy.modal.show({
                title: _l("Sign out"),
                body: "Do you want to continue and sign out of all active sessions?",
                buttons: {
                    Cancel: function() {
                        Galaxy.modal.hide();
                    },
                    "Sign out": function() {
                        window.location.href = `${getAppRoot()}user/logout?session_csrf_token=${
                            Galaxy.session_csrf_token
                        }`;
                    }
                }
            });
        }
    }
};
</script>

<style>
.pref-content {
    width: calc(100% - 40px);
}
.pref-icon {
    width: 40px;
}
</style>
