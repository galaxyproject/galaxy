<template>
    <div v-on:click="printNotifications()">
        <b-nav-item> <notification-bell icon-color="white" :count="count" :size="20"> </notification-bell> </b-nav-item>
    </div>
</template>

<script>
import axios from "axios";
import { BNav, BNavItemDropdown, BNavItem } from "bootstrap-vue";
import { getGalaxyInstance } from "app";
import LoadingSpan from "components/LoadingSpan";
import NotificationBell from "vue-notification-bell";
import { errorMessageAsString } from "utils/simple-error";

export default {
    components: {
        LoadingSpan,
        NotificationBell,
        BNavItem,
        BNavItemDropdown,
        BNav,
    },
    data() {
        const Galaxy = getGalaxyInstance();
        return {
            notificationsUrl: `${Galaxy.root}api/notifications`,
            notifications: null,
            errorMessage: null,
            showNotifications: false,
        };
    },
    created() {
        this.loadNotifications();
    },
    computed: {
        loading() {
            return this.notifications == null;
        },
        count() {
            return this.notifications ? this.notifications.length : 0;
        },
    },
    methods: {
        loadNotifications() {
            setInterval(() => {
                axios
                    .get(this.notificationsUrl)
                    .then((response) => {
                        this.notifications = response.data;
                    })
                    .catch(this.handleError);
            }, 60000);
        },
        handleError(error) {
            this.errorMessage = errorMessageAsString(error);
        },
        printNotifications() {
            console.log("pushing to router");
            this.$router.push("notifications");
        },
        toggleShowNotifications() {
            console.log("inside show notifications");
            this.showNotifications = !this.showNotifications;
        },
    },
};
</script>
