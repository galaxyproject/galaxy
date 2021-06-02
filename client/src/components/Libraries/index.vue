<template>
    <CurrentUser v-slot="{ user }">
        <section v-if="user">
            <header>
                <h1>Data Libraries</h1>
                <b-breadcrumb>
                    <b-breadcrumb-item :to="{ name: 'LibraryList' }">
                        <span v-localize>Data Libraries</span>
                    </b-breadcrumb-item>
                </b-breadcrumb>
            </header>
            <router-view :user="user"></router-view>
        </section>
    </CurrentUser>
</template>

<script>
import router from "./router";
import CurrentUser from "components/providers/CurrentUser";

export default {
    router,
    components: {
        CurrentUser,
    },
    data() {
        return {
            debug: true,
        };
    },
    provide() {
        return {
            debug: this.debug,
            log: this.log,
            warn: this.warn,
        };
    },
    methods: {
        log(...args) {
            if (this.debug) {
                console.log("Libraries ->", ...args);
            }
        },
        warn(...args) {
            console.warn("Libraries ->", ...args);
        },
    },
};
</script>
