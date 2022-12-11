<template>
    <div id="columns">
        <div id="center">
            <div class="center-container">
                <div class="center-panel" style="display: block">
                    <ChangePassword
                        v-if="hasToken"
                        :expired-user="$route.query.expired_user"
                        :message-text="$route.query.message"
                        :message-variant="$route.query.status"
                        :token="$route.query.token" />
                    <LoginIndex
                        v-else
                        :allow-user-creation="config.allow_user_creation"
                        :enable-oidc="config.enable_oidc"
                        :mailing-join-addr="config.mailing_join_addr"
                        :prefer-custos-login="config.prefer_custos_login"
                        :redirect="$route.query.redirect"
                        :registration-warning-message="config.registration_warning_message"
                        :server-mail-configured="config.server_mail_configured"
                        :session-csrf-token="sessionCsrfToken"
                        :show-welcome-with-login="config.show_welcome_with_login"
                        :terms-url="config.terms_url"
                        :welcome-url="config.welcome_url" />
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import LoginIndex from "components/Login/LoginIndex";
import ChangePassword from "components/Login/ChangePassword";

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
        sessionCsrfToken() {
            return getGalaxyInstance().session_csrf_token;
        },
    },
};
</script>
