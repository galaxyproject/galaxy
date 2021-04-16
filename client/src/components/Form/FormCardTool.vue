<template>
    <div class="ui-portlet-section">
        <div class="portlet-header">
            <div class="portlet-operations">
                <slot name="operations" />
                <b-button
                    v-if="showAddFavorite"
                    role="button"
                    title="Add to Favorites"
                    variant="link"
                    size="sm"
                    class="float-right py-0 px-1"
                    v-b-tooltip.hover
                    @click="onAddFavorite"
                >
                    <span class="fa fa-star-o" />
                </b-button>
                <b-button
                    v-else
                    role="button"
                    title="Remove from Favorites"
                    variant="link"
                    size="sm"
                    class="float-right py-0 px-1"
                    v-b-tooltip.hover
                    @click="onRemoveFavorite"
                >
                    <span class="fa fa-star" />
                </b-button>
            </div>
            <div class="portlet-title">
                <i class="portlet-title-icon fa mr-1 fa-wrench" style="display: inline"></i>
                <span class="portlet-title-text">
                    <b itemprop="name">{{ title }}</b> <span itemprop="description">{{ description }}</span>
                    (Galaxy Verson {{ version }})
                </span>
            </div>
        </div>
        <div class="portlet-content">
            <slot name="body" />
        </div>
    </div>
</template>
<script>
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import ariaAlert from "utils/ariaAlert";
import axios from "axios";

export default {
    props: {
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            required: false,
        },
        version: {
            type: String,
            required: false,
        },
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            isFavorite: this.getFavorite(),
        };
    },
    computed: {
        showAddFavorite() {
            return !this.getUser().isAnonymous() && !this.isFavorite;
        },
    },
    methods: {
        getUser() {
            const galaxy = getGalaxyInstance();
            return galaxy.user;
        },
        getFavorite() {
            return this.getUser().getFavorites().tools.indexOf(this.id) >= 0;
        },
        onAddFavorite() {
            const user = this.getUser();
            axios
                .put(`${getAppRoot()}api/users/${user.id}/favorites/tools`, { object_id: this.id })
                .then((response) => {
                    user.updateFavorites("tools", response.data);
                    this.isFavorite = this.getFavorite();
                    ariaAlert("added to favorites");
                });
        },
        onRemoveFavorite() {
            const user = this.getUser();
            axios
                .delete(`${getAppRoot()}api/users/${user.id}/favorites/tools/${encodeURIComponent(this.id)}`)
                .then((response) => {
                    user.updateFavorites("tools", response.data);
                    this.isFavorite = this.getFavorite();
                    ariaAlert("removed from favorites");
                });
        },
    },
};
</script>
