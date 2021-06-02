/**
 * This provider leverages reactive user and filter props to tell the store when to reload the list
 * of libraries which are shared throughout this module.
 */

import { mapActions, mapGetters } from "vuex";
import { LibraryParams } from "../model";
import User from "store/userStore/User";

export default {
    inject: ["log"],
    props: {
        user: { type: User, required: true },
        filters: { type: LibraryParams, required: true },
    },
    computed: {
        ...mapGetters("library", ["libraries", "busy"]),

        filteredLibraries() {
            return this.libraries.filter((lib) => this.filters.matchLibrary(lib));
        },
    },
    methods: {
        ...mapActions("library", ["loadLibraries"]),
    },
    watch: {
        user: {
            immediate: true,
            handler() {
                this.loadLibraries();
            },
        },
    },
    render() {
        return this.$scopedSlots.default({
            busy: this.busy,
            libraries: this.filteredLibraries,
        });
    },
};
