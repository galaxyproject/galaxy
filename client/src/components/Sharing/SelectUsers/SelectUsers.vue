<template>
    <div>
        <div v-if="isExposeEmail">
            <multiselect
                v-model="selectedUsers"
                :options="usersList"
                :clear-on-select="true"
                :preserve-search="true"
                :multiple="true"
                @select="onSelect"
                @remove="onRemove"
                label="email"
                track-by="id"
                @search-change="searchChanged"
                :internal-search="false"
            >
                <template slot="noOptions">
                    <div>
                        {{ emptyResult }}
                    </div>
                </template>
            </multiselect>
        </div>
        <div v-else>
            <b-input-group class="mt-3">
                <b-form-input v-model="email_input"></b-form-input>
                <b-input-group-append>
                    <b-button @click="onSelect(email_input)" variant="info">Submit</b-button>
                </b-input-group-append>
            </b-input-group>
        </div>
    </div>
</template>

<script>
import { Services } from "components/Sharing/services";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import Multiselect from "vue-multiselect";

export default {
    components: {
        Multiselect,
    },
    props: {
        users_shared_with: {
            type: Array,
        },
        share_with: {
            type: String,
            required: true,
        },
        unshare_with: {
            type: String,
            required: true,
        },
        pluralName: {
            type: String,
            required: true,
        },
        id: {
            type: String,
            required: true,
        },
        isExposeEmail: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        const galaxy = getGalaxyInstance();
        return {
            email_input: "",
            usersList: [],
            selectedUsers: this.users_shared_with,
            isAdmin: galaxy.user.isAdmin(),
            emptyResult: "Please enter user email",
            root: getAppRoot(),
        };
    },
    created() {
        this.services = new Services({ root: this.root });
        console.log(getGalaxyInstance().config);
        console.log("users_shared_with", this.users_shared_with);
    },
    methods: {
        onSelect(user) {
            this.services.saveSharingPreferences(this.pluralName, this.id, this.share_with, user.id);
        },
        onRemove(user) {
            console.log(user);
            this.services.saveSharingPreferences(this.pluralName, this.id, this.share_with, user.id);
        },
        searchChanged(searchValue) {
            if (searchValue === "") {
                this.usersList = [];
            } else {
                this.services.getUsers(searchValue).then((usersList) => {
                    this.usersList = usersList;
                });
            }
        },
    },
};
</script>

<style scoped></style>
