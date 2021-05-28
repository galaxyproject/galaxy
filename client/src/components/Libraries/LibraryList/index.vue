<template>
    <LibraryListProvider v-if="user" :user="user" :filters="filters" v-slot="{ libraries }">
        <Listing :user="user" :filters.sync="filters" :libraries="libraries" />
    </LibraryListProvider>
</template>

<script>
import { LibraryParams } from "../model";
import LibraryListProvider from "./LibraryListProvider";
import Listing from "./Listing";
import User from "store/userStore/User";

export default {
    components: {
        LibraryListProvider,
        Listing,
    },
    props: {
        user: { type: User, required: true },
    },
    data() {
        return {
            filters: LibraryParams.create({ showRestricted: true }),
        };
    },
};
</script>


