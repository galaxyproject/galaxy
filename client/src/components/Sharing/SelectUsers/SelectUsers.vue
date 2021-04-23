<template>
    <div>
        <div >
            <multiselect
                v-model="selectedUsers"
                :options="usersList"
                :clear-on-select="true"
                :preserve-search="true"
                :multiple="true"
                @select="onSelect(id)"
                @remove="onRemove(id)"
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
    },
    methods: {
        onSelect(user) {
            this.services.saveSharingPreferences(this.pluralName, this.id, this.share_with, user);
        },
        onRemove(user) {
            console.log(user);
            this.services.saveSharingPreferences(this.pluralName, this.id, this.share_with, user);
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
