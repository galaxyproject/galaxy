<template>
    <div id="form-userkeys" class="toolForm" v-cloak>
        <div class="toolFormTitle">User Information</div>
        <div v-if="users && users.length > 0">
            <table class="grid">
                <thead><th>Encoded UID</th><th>Email</th><th>API Key</th><th>Actions</th></thead>
                <tbody>
                    <tr v-for="user in users">
                        <td>
                            {{ user.uid }}
                        </td>
                        <td>
                            {{ user.email }}
                        </td>
                        <td>
                            {{ user.key }}
                        </td>
                        <td>
                            <input type="button" value="Generate a new key now" v-on:click="generateKey( user.uid )" />
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div v-else>
            <div>No user information available</div>
        </div>
        <div style="clear: both"></div>
    </div>
</template>

<script>
import axios from "axios";

export default {
    data() {
        return {
            // Should really do something with errors here.  Eventually.
            users: [],
            errors: []
        };
    },
    created: function() {
        axios
            .get(`${Galaxy.root}userskeys/all_users`)
            .then(response => {
                this.users = response.data;
            })
            .catch(e => {
                this.errors.push(e);
            });
    },
    methods: {
        generateKey: function(id) {
            axios
                .get(`${Galaxy.root}userskeys/admin_api_keys`, { params: { uid: id } })
                .then(response => {
                    this.users = response.data;
                })
                .catch(e => {
                    this.errors.push(e);
                });
        }
    }
};
</script>
<style>
</style>
