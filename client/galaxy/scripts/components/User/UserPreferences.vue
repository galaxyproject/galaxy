<template>
    <div>
        <h2>User preferences</h2>
        <p>You are logged in as <strong>{{ email }}</strong>.</p>
        <table>
            <tbody>
            <tr v-for="link in activeLinks">
                <td class="align-top">
                    <i :class="`ml-3 mr-3 fa fa-lg ${link.icon}`">
                    </i>
                </td>
                <td>
                    <a v-if="link.onclick" @click="link.onclick" href="javascript:void(0)"><b>{{link.title}}</b></a>
                    <a v-else :href="`${baseUrl}/${link.action}`"><b>{{link.title}}</b></a>
                    <div class="form-text text-muted">
                        {{link.description}}
                    </div>
                </td>
            </tr>
            </tbody>
        </table>
        <p class="mt-2">You are using <strong>{{ diskUsage }}</strong> of disk space in this Galaxy instance.
            {{ quotaUsageString }}
            Is your usage more than expected? See the <a
                    href="https://galaxyproject.org/learn/managing-datasets/" target="_blank"><b>documentation</b></a>
            for tips on how to find all of the data in your account.</p></div>
</template>

<script>
    import {getGalaxyInstance} from "app";
    import {getAppRoot} from "onload/loadConfig";
    import _l from "utils/localization";
    import axios from "axios";
    import Ui from "mvc/ui/ui-misc";
    import QueryStringParsing from "utils/query-string-parsing";

    export default {
        data() {
            const Galaxy = getGalaxyInstance();
            const config = Galaxy.config;
            return {
                user: Galaxy.user,
                email: "",
                diskUsage: "",
                quotaString: "",
                baseUrl: `${getAppRoot()}user`,
                links: [
                    {
                        action: `information`,
                        title: _l("Manage information"),
                        description: "Edit your email, addresses and custom parameters or change your public name.",
                        url: `api/users/${Galaxy.user.id}/information/inputs`,
                        icon: "fa-user",
                        redirect: "user",
                        shouldRender: !config.use_remote_user,
                    },
                    {
                        action: "password",
                        title: _l("Change password"),
                        description: _l("Allows you to change your login credentials."),
                        icon: "fa-unlock-alt",
                        url: `api/users/${Galaxy.user.id}/password/inputs`,
                        submit_title: "Save password",
                        redirect: "user",
                        shouldRender: !config.use_remote_user,
                    },
                    {
                        action: "communication",
                        title: _l("Change communication settings"),
                        description: _l("Enable or disable the communication feature to chat with other users."),
                        url: `api/users/${Galaxy.user.id}/communication/inputs`,
                        icon: "fa-comments-o",
                        redirect: "user",
                        shouldRender: !!config.enable_communication_server,
                    },
                    {
                        action: "permissions",
                        title: _l("Set dataset permissions for new histories"),
                        description:
                            "Grant others default access to newly created histories. Changes made here will only affect histories created after these settings have been stored.",
                        url: `api/users/${Galaxy.user.id}/permissions/inputs`,
                        icon: "fa-users",
                        submit_title: "Save permissions",
                        redirect: "user"
                    },
                    {
                        action: "make_data_private",
                        title: _l("Make all data private"),
                        description: _l("Click here to make all data private."),
                        icon: "fa-lock",
                        onclick: this.makeDataPrivate,
                    },
                    {
                        action: "api_key",
                        title: _l("Manage API key"),
                        description: _l("Access your current API key or create a new one."),
                        url: `api/users/${Galaxy.user.id}/api_key/inputs`,
                        icon: "fa-key",
                        submit_title: "Create a new key",
                        submit_icon: "fa-check"
                    },
                    {
                        action: "cloud_auth",
                        title: _l("Manage Cloud Authorization"),
                        description: _l(
                            "Add or modify the configuration that grants Galaxy to access your cloud-based resources."
                        ),
                        icon: "fa-cloud",
                        submit_title: "Create a new key",
                        submit_icon: "fa-check"
                    },
                    {
                        action: "toolbox_filters",
                        title: _l("Manage Toolbox filters"),
                        description: _l("Customize your Toolbox by displaying or omitting sets of Tools."),
                        url: `api/users/${Galaxy.user.id}/toolbox_filters/inputs`,
                        icon: "fa-filter",
                        submit_title: "Save filters",
                        redirect: "user",
                        shouldRender: !!config.has_user_tool_filters,
                    },
                    {
                        action: "custom_builds",
                        title: _l("Manage custom builds"),
                        description: _l("Add or remove custom builds using history datasets."),
                        icon: "fa-cubes",
                        onclick: this.openManageCustomBuilds,
                    },
                    {
                        action: "genomespace",
                        title: _l("Request GenomeSpace token"),
                        description: _l("Requests token through OpenID."),
                        icon: "fa-openid",
                        onclick: this.requestGenomeSpace,
                    },
                    {
                        action: "logout",
                        title: _l("Sign out"),
                        description: _l("Click here to sign out of all sessions."),
                        icon: "fa-sign-out",
                        onclick: this.signOut,
                        shouldRender: !!Galaxy.session_csrf_token
                    }

                ]
            }
        },
        created() {
            const Galaxy = getGalaxyInstance();
            const config = Galaxy.config;
            const message = QueryStringParsing.get("message");
            const status = QueryStringParsing.get("status");

            if (message && status) {
                $(this.$el).prepend(new Ui.Message({message: message, status: status}).$el);
            }

            axios.get(`${getAppRoot()}api/users/${Galaxy.user.id}`)
                .then(response => {
                    this.email = response.data.email
                    this.diskUsage = response.data.nice_total_disk_usage;
                    this.quotaUsageString =  config.enable_quotas ? `Your disk quota is: <strong>${response.data.quota}</strong>.` : "";
                })
        },
        computed: {
            activeLinks() {
                return this.links.filter(function (link) {
                    return link.shouldRender !== false;
                })
            }
        },
        methods: {
            openManageCustomBuilds() {
                const Galaxy = getGalaxyInstance();
                Galaxy.page.router.push(`${getAppRoot()}custom_builds`);
            },
            makeDataPrivate() {
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
                    $.post(`${Galaxy.root}history/make_private`, {all_histories: true}, () => {
                        Galaxy.modal.show({
                            title: _l("Datasets are now private"),
                            body: `All of your histories and datsets have been made private.  If you'd like to make all *future* histories private please use the <a href="${
                                Galaxy.root
                                }user/permissions">User Permissions</a> interface.`,
                            buttons: {
                                Close: function () {
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
                        Cancel: function () {
                            Galaxy.modal.hide();
                        },
                        "Sign out": function () {
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
