<template>
    <div id="columns">
        <div id="center">
            <div class="center-container">
                <div class="center-panel" style="display: block">
                    <ChangePassword
                        v-if="hasToken"
                        :token="$route.query.token"
                        :expired-user="$route.query.expired_user"
                        :message-text="$route.query.message"
                        :message-variant="$route.query.status" />
                    <LoginIndex
                        v-else
                        :show_welcome_with_login="config.show_welcome_with_login"
                        :welcome_url="config.welcome_url"
                        :terms_url="config.terms_url"
                        :registration_warning_message="config.registration_warning_message"
                        :mailing_join_addr="config.mailing_join_addr"
                        :server_mail_configured="config.server_mail_configured" />
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import LoginIndex from "components/login/LoginIndex";
import ChangePassword from "components/login/ChangePassword";

export default {
    components: {
        ChangePassword,
        LoginIndex,
    },
    computed: {
        config() {
            return getGalaxyInstance().config;
        },
        hasToken() {
            return this.$route.query.token || this.$route.query.expired_user;
        },
    },
};
</script>
