<template>
    <div>
        <h2>Share or Publish {{item_class_name}} '{{item_name}}'</h2>
        <div v-if="!has_username">
            <div>To make a {{item_class_name_lc}} accessible via link or publish it, you must create a public username:</div>
            <div v-if="err_msg" class="ui-message ui-show alert alert-danger">
                {{ err_msg }}
            </div>
            <form class="form-group">
              <label/>
              <input class="form-control" type="text" v-model="username"/>
            </form>
            <button type="submit" class="btn btn-primary" @click="setUsername()">Set Username</button>
        </div>
        <div v-else>
            <br/>
            <h3>Make {{item_class_name}} Accessible via Link and Publish It</h3>
            <div v-if="item_importable">
                This {{item_class_name_lc}} is currently <strong>{{item_status}}</strong>.
                <div>
                    <p>Anyone can view and import this {{item_class_name_lc}} by visiting the following URL:
                    <blockquote>
                        <a id="item-url" href="{{item_url}}" target="_top">{{item_url}}</a>
                    </blockquote>
                    <div v-if="item_published">
                        <p>This {{item_class_name_lc}} is publicly listed and searchable in Galaxy's <a href='{{list_url}}' target="_top">Published {{item_class_plural_name}}</a> section. You can:</p>
                        <div>
                        <form action="${h.url_for( controller=controller_name, action='sharing', id=trans.security.encode_id( item.id ) )}" method="POST">
                            <div v-if="!item_published">
                                ## Item is importable but not published. User can disable importable or publish.
                                <input class="action-button" type="submit" name="disable_link_access" value="Disable Access to {{item_class_name}} Link">
                                <div class="toolParamHelp">Disables {{item_class_name_lc}}'s link so that it is not accessible.</div>
                                <br/>
                                <input class="action-button" type="submit" name="publish" value="Publish {{item_class_name}}" method="POST">
                                <div class="toolParamHelp">Publishes the {{item_class_name_lc}} to Galaxy's <a href='{{list_url}}' target="_top">Published {{item_class_plural_name}}</a> section, where it is publicly listed and searchable.</div>
                                <br/>
                            </div>
                            <div v-else>
                                ## Item is importable and published. User can unpublish or disable import and unpublish.
                                <input class="action-button" type="submit" name="unpublish" value="Unpublish {{item_class_name}}">
                                <div class="toolParamHelp">Removes this {{item_class_name_lc}} from Galaxy's <a href='${h.url_for(controller=controller_list, action='list_published' )}' target="_top">Published ${item_class_plural_name}</a> section so that it is not publicly listed or searchable.</div>
                                <br />
                                <input class="action-button" type="submit" name="disable_link_access_and_unpublish" value="Disable Access to {{item_class_name}} via Link and Unpublish">
                                <div class="toolParamHelp">Disables this {{item_class_name_lc}}'s link so that it is not accessible and removes {{item_class_name_lc}} from Galaxy's <a href='${h.url_for(controller=controller_list, action='list_published' )}' target='_top'>Published {{item_class_plural_name}}</a> section so that it is not publicly listed or searchable.</div>
                            </div>
                        </form>
                    </div>
                    <div v-else>
                        <p>This {{item_class_name_lc}} is currently restricted so that only you and the users listed below can access it. You can:</p>
                        <form action="${h.url_for(controller=controller_name, action='sharing', id=trans.security.encode_id(item.id) )}" method="POST">
                            <input class="action-button" type="submit" name="make_accessible_via_link" value="Make ${item_class_name} Accessible via Link">
                            <div class="toolParamHelp">Generates a web link that you can share with other people so that they can view and import the ${item_class_name_lc}.</div>

                            <br />
                            <input class="action-button" type="submit" name="make_accessible_and_publish" value="Make ${item_class_name} Accessible and Publish" method="POST">
                            <div class="toolParamHelp">Makes the ${item_class_name_lc} accessible via link (see above) and publishes the ${item_class_name_lc} to Galaxy's <a href='${h.url_for(controller=controller_list, action='list_published' )}' target='_top'>Published ${item_class_plural_name}</a> section, where it is publicly listed and searchable.</div>
                        </form>
                    </div>
                </div>
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
        },
        item_status() {
            return item_published ? "accessible via link" ? "accessible via link and published";
        },
        item_url() {
            return `${Galaxy.root}${this.item_controller}/display_by_username_and_slug/?username=this.username&slug=item_slug&qualified=true`;
        },
        list_url() {
            return `${Galaxy.root}${this.item_controller}/list_published`;
        }
    },
    data() {
        return {
            item_class_name: "class_name",
            item_class_plural_name: "plural_name",
            item_name: "name",
            item_importable: true,
            item_published: true,
            item_slug: "slug",
            item_controller: "item_controller",
            list_controller: "list_controller",
            username: "",
            has_username: true,
            err_msg: null,
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
