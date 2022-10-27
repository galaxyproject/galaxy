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
                        :allow-user-creation="config.allow_user_creation"
                        :show-welcome-with-login="config.show_welcome_with_login"
                        :welcome-url="config.welcome_url"
                        :terms-url="config.terms_url"
                        :redirect="$route.query.redirect"
                        :registration-warning-message="config.registration_warning_message"
                        :mailing-join-addr="config.mailing_join_addr"
                        :server-mail-configured="config.server_mail_configured"
                        :enable-oidc="config.enable_oidc"
                        :prefer-custos-login="config.prefer_custos_login"
                        :session-csrf-token="sessionCsrfToken" />
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
        sessionCsrfToken() {
            return getGalaxyInstance().session_csrf_token;
        },
    },
};
</script>
