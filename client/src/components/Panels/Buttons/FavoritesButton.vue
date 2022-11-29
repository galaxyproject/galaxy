<template>
    <b-button
        v-b-tooltip.hover
        class="panel-header-button-toolbox"
        size="sm"
        variant="link"
        aria-label="Show favorite tools"
        :disabled="currentUser.isAnonymous"
        :title="tooltipText"
        @click="onFavorites">
        <FontAwesomeIcon v-if="toggle" :icon="['fas', 'star']" />
        <FontAwesomeIcon v-else :icon="['far', 'star']" />
    </b-button>
</template>

<script>
import { mapGetters } from "vuex";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar as fasStar } from "@fortawesome/free-solid-svg-icons";
import { faStar as farStar } from "@fortawesome/free-regular-svg-icons";

library.add(fasStar, farStar);

export default {
    name: "FavoritesButton",
    components: { FontAwesomeIcon },
    props: {
        query: {
            type: String,
        },
    },
    data() {
        return {
            searchKey: "#favorites",
            toggle: false,
        };
    },
    computed: {
        ...mapGetters("user", ["currentUser"]),

        tooltipText() {
            if (this.currentUser.isAnonymous) {
                return this.l("Log in to Favorite Tools");
            } else {
                if (this.toggle) {
                    return this.l("Clear");
                } else {
                    return this.l("Show favorites");
                }
            }
        },
    },
    watch: {
        query() {
            this.toggle = this.query == this.searchKey;
        },
    },
    methods: {
        onFavorites() {
            this.toggle = !this.toggle;
            if (this.toggle) {
                this.$emit("onFavorites", this.searchKey);
            } else {
                this.$emit("onFavorites", null);
            }
        },
    },
};
</script>
