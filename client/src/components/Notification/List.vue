<template>
    <div class="notifications-card">
        <b-alert variant="error" show v-if="errorMessage"> </b-alert>
        <loading-span v-if="loading" message="Loading notifications" />
        <ul id="notifications" v-else>
            <li v-for="notifiation in notifications" :key="notifications" :data-extension-target="notifications">
                <span
                    <div class="ui success message">
                        <i class="close icon"></i>
                        <div class="header">
                           {{notifiation.message_text}}
                        </div>
                    </div>
                </span>
            </li>
        </ul>
    </div>
</template>

<script>
import axios from "axios";
import { getGalaxyInstance } from "app";
import LoadingSpan from "components/LoadingSpan";
import { errorMessageAsString } from "utils/simple-error";

export default {
    components: {
        LoadingSpan,
    },
    data() {
        const Galaxy = getGalaxyInstance();
        return {
            notificationsUrl: `${Galaxy.root}api/notifications`,
            notifications: null,
            errorMessage: null,
        };
    },
    created() {
        this.loadNotifications();
    },
    computed: {
        loading() {
            return this.notifications == null;
        },
    },
    methods: {
        loadNotifications() {
            axios
                .get(this.NotificationsUrl)
                .then((response) => {
                    this.notifications = response.data;
                })
                .catch(this.handleError);
        },
        handleError(error) {
            this.errorMessage = errorMessageAsString(error);
        },
    },
};
</script>