import { mapGetters, mapActions } from "vuex";

export default {
    props: {
        siteDefaultPanelView: {
            type: String,
            required: true,
        },
    },
    computed: {
        ...mapGetters("panels", ["currentPanel", "currentPanelView"]),
    },
    methods: {
        ...mapActions("panels", ["initCurrentPanelView"]),
    },
    created() {
        this.initCurrentPanelView(this.siteDefaultPanelView);
    },
    render() {
        return this.$scopedSlots.default({
            currentPanel: this.currentPanel,
            currentPanelView: this.currentPanelView,
        });
    },
};
