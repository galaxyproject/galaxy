import { mapGetters, mapActions } from "vuex";

export default {
    props: {
        siteDefaultPanelView: {
            type: String,
            required: true,
        },
        setDefaultPanelView: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        ...mapGetters("panels", ["currentPanel", "currentPanelView"]),
    },
    methods: {
        ...mapActions("panels", ["initCurrentPanelView", "setCurrentPanelView"]),
    },
    created() {
        if (this.setDefaultPanelView) {
            this.setCurrentPanelView(this.siteDefaultPanelView);
        } else {
            this.initCurrentPanelView(this.siteDefaultPanelView);
        }
    },
    render() {
        return this.$scopedSlots.default({
            currentPanel: this.currentPanel,
            currentPanelView: this.currentPanelView,
        });
    },
};
