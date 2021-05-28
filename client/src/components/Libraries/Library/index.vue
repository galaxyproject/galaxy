<template>
    <div>
        <LibraryDetails :value="library" @input="saveLibrary" />
        <router-view :library="library"></router-view>
    </div>
</template>

<script>
import { getLibraryById, saveLibrary } from "../model";
import User from "store/userStore/User";
import LibraryDetails from "./LibraryDetails";

export default {
    components: {
        LibraryDetails,
    },
    props: {
        user: { type: User, required: true },
        libraryId: { type: String, required: true },
    },
    data() {
        return {
            library: {},
        };
    },
    created() {
        this.loadLibrary(this.libraryId);
    },
    methods: {
        async loadLibrary(id) {
            getLibraryById(id).then((result) => (this.library = result));
        },
        async saveLibrary(lib) {
            const result = await saveLibrary(lib);
            console.log("saveLibrary", result);
        },
    },
};
</script>