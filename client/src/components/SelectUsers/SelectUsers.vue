<template>
    <div>
        <multiselect
            v-model="selectedUsers"
            :options="usersList"
            :clear-on-select="true"
            :preserve-search="true"
            :multiple="true"
            :custom-label="nameWithLang"
            track-by="id"
            @input="valueChanged"
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
</template>

<script>
import { Services } from "./services";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import Multiselect from "vue-multiselect";

export default {
    components: {
        Multiselect,
    },
    data() {
        const galaxy = getGalaxyInstance();
        return {
            usersList: [],
            selectedUsers: undefined,
            isAdmin: galaxy.user.isAdmin(),
            emptyResult: "Please enter user email",
            root: getAppRoot(),
        };
    },
    created() {
        this.services = new Services({ root: this.root });
    },
    methods: {
        nameWithLang({ username, email }) {
            return `${username} — ${email}`;
        },
        valueChanged() {
            this.services.saveSharingPreferences(this.selectedUsers)
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
