<template>
    <div v-if="library">
        <LibraryDetails :library="library" @update:library="updateLibrary" />
        <router-view :library="library"></router-view>
    </div>
</template>

<script>
import { getLibraryById, saveLibrary } from "../model";
import LibraryDetails from "./LibraryDetails";

export default {
    components: {
        LibraryDetails,
    },
    props: {
        libraryId: { type: String, required: true },
    },
    data() {
        return {
            library: null,
        };
    },
    async created() {
        this.library = await getLibraryById(this.libraryId);
    },
    methods: {
        async updateLibrary(lib) {
            this.library = await saveLibrary(lib);
        },
    },
};
</script>
