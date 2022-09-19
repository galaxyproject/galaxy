import { mapGetters, mapActions } from "vuex";

export default {
    computed: {
        ...mapGetters("user", ["currentUser"]),
    },
    methods: {
        ...mapActions("user", ["loadUser"]),
    },
    created() {
        this.loadUser();
    },
    render() {
        return this.$scopedSlots.default({
            user: this.currentUser,
        });
    },
};
