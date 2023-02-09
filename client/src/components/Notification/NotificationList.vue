<template>
    <div class="notifications-card">
        <h3>Pending notifications</h3>
        <!-- <notification-bell @click="loadNotifications()"> Notification Bell</notification-bell> -->
        <!-- <button v-on:click="loadNotifications()"> Notification Bell</button> -->
        <b-alert v-if="errorMessage" variant="error" show> </b-alert>
        <loading-span v-if="loading" message="Loading notifications" />
        <ul v-else id="notifications">
            <li v-for="notification in notifications" :key="notification.id">
                <span>
                    <div class="ui success message">
                        <i class="close icon"></i>
                        <div class="header">
                            {{ notification.message }}
                        </div>
                    </div>
                </span>
            </li>
        </ul>
        <h3>Create new notification</h3>
        <p>Notification Message is: {{ message }}</p>
        <input v-model="message" placeholder="edit me" @keyup.enter="putNotification($event)" />
        <button @click="putNotification(message)">Create Message</button>
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
            message: "",
        };
    },
    computed: {
        loading() {
            return this.notifications == null;
        },
    },
    created() {
        this.loadNotifications();
    },
    methods: {
        loadNotifications() {
            axios
                .get(this.notificationsUrl)
                .then((response) => {
                    this.notifications = response.data;
                })
                .catch(this.handleError);
        },
        putNotification(message) {
            const payload = { message };
            axios
                .post(this.notificationsUrl, payload)
                .then((response) => {
                    console.log(response);
                })
                .catch(this.handleError);
        },
        handleError(error) {
            this.errorMessage = errorMessageAsString(error);
        },
    },
};
</script>
