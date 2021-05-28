import { LibraryParams, getLibraries } from "../model";
import User from "store/userStore/User";

export default {
    inject: ["log"],
    props: {
        user: { type: User, required: true },
        filters: { type: LibraryParams, required: true },
    },
    data() {
        return {
            loadPromise: null,
            libraries: [],
        };
    },
    computed: {
        filteredLibraries() {
            return this.libraries.filter((lib) => this.filters.matchLibrary(lib));
        },
        busy() {
            return this.loadPromise !== null;
        },
        // Vue's observability system has no "combineLatest"
        userAndFilters() {
            return { user: this.user, filters: this.filters };
        },
    },
    watch: {
        userAndFilters: {
            immediate: true,
            handler(newStuff, oldStuff) {
                let load = false;
                if (!oldStuff) {
                    load = true;
                } else {
                    const { user: newUser, filters: newFilters } = newStuff;
                    const { user: oldUser, filters: oldFilters } = oldStuff;
                    load = !newUser.isSameUser(oldUser) || newFilters.searchQuery != oldFilters.searchQuery;
                }
                if (load) {
                    this.loadLibraries();
                }
            },
        },
    },
    methods: {
        loadLibraries(label) {
            this.log("label", label);
            const loadPromise = this?.loadPromise || getLibraries(this.filters);
            this.loadPromise = loadPromise
                .then((libs) => {
                    this.libraries = libs;
                })
                .catch((err) => {
                    this.log("error loading list of libraries", err);
                })
                .finally(() => {
                    this.loadPromise = null;
                });
        },
        // async createLibrary() {
        //     console.log("createLibrary", arguments);
        // },
        // async saveLibrary(library) {
        //     const response = await this.api.patch(`libraries/${library.id}`, library);
        //     console.log("saveLibrary", library, response);
        // },
        // async deleteLibrary(isUndelete) {
        //     console.log("deleteLibrary", isUndelete);
        // },
    },
    render() {
        return this.$scopedSlots.default({
            busy: this.busy,
            libraries: this.filteredLibraries,
            // handlers: {
            //     createLibrary: this.createLibrary,
            //     saveLibrary: this.saveLibrary,
            //     deleteLibrary: this.deleteLibrary,
            // },
        });
    },
};
