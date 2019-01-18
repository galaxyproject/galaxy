<template>
    <div>
        <b-tabs>
            <b-tab title="Login" active>
                <login
                    :show_welcome_with_login="show_welcome_with_login"
                    :welcome_url="welcome_url"
                />
            </b-tab>
            <b-tab title="Register">
                <register
                    :registration_warning_message="registration_warning_message"
                    :mailing_join_addr="mailing_join_addr"
                    :smtp_server="smtp_server"
                />
            </b-tab>
        </b-tabs>
    </div>
</template>
<script>
import Login from "components/login/Login.vue";
import Register from "components/login/Register.vue";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    components: {
        login: Login,
        register: Register
    },
    props: {
        show_welcome_with_login: {
            type: Boolean,
            required: false
        },
        welcome_url: {
            type: String,
            required: false
        },
        registration_warning_message: {
            type: String,
            required: false
        },
        mailing_join_addr: {
            type: String,
            required: false
        },
        smtp_server: {
            type: String,
            required: false
        }
    }
};
</script>
