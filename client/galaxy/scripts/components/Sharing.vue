<template>
    <div>
        <h2>Share or Publish {{item_class_name}} '{{item_name}}'</h2>
        <div v-if="!has_username">
            <div>To make a {{item_class_name_lc}} accessible via link or publish it, you must create a public username:</div>
            <div class="ui-message ui-show alert alert-danger">
                {{ err_msg }}
            </div>
            <form class="form-group">
              <label/>
              <input class="form-control" type="text" v-model="username"/>
            </form>
            <button type="submit" class="btn btn-primary" @click="setUsername()">Set Username</button>
        </div>
        <div v-else>
            <h3>Make {{item_class_name}} Accessible via Link and Publish It</h3>
        </div>
    </div>
</template>

<script>
import axios from "axios";
export default {
    props: {
        /*id: {
            type: String,
            required: true
        }*/
    },
    computed: {
        item_class_name_lc() {
            return this.item_class_name.toLowerCase();
        },
        item_class_plural_name_lc() {
            return this.item_class_plural_name.toLowerCase();
        }
    },
    data() {
        return {
            item_class_name: "class_name",
            item_class_plural_name: "plural_name",
            item_name: "name",
            username: "",
            has_username: false,
            err_msg: "test",
            user: Galaxy.user
        };
    },
    created: function() {
    },
    methods: {
        setUsername: function() {
            axios
                .put(`${Galaxy.root}api/users/${Galaxy.user.id}/information/inputs`, {
                    username: this.username
                })
                .then(response => this.has_username = true)
                .catch(error => this.err_msg = error.response.data.err_msg);
        }
    },
    updated: function() {
    }
};
</script>

<style>
.ui-show {
    display: block;
}
</style>
