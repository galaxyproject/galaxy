import { mapGetters, mapActions } from "vuex";

export default {
    props: {
        panelView: {
            type: String,
            required: true,
        },
        setDefault: {
            type: Boolean,
            required: false,
            default: true,
        },
    },
    computed: {
        ...mapGetters("panels", ["currentPanel", "currentPanelView", "panel"]),
        localPanelView() {
            return this.setDefault ? this.currentPanelView : this.panelView;
        },
        localPanel() {
            return this.setDefault ? this.currentPanel : this.panel(this.panelView);
        },
    },
    methods: {
        ...mapActions("panels", ["initCurrentPanelView", "fetchPanel"]),
    },
    created() {
        if (this.setDefault) {
            this.initCurrentPanelView(this.panelView);
        } else {
            this.fetchPanel(this.panelView);
        }
    },
    render() {
        return this.$scopedSlots.default({
            currentPanel: this.localPanel,
            currentPanelView: this.localPanelView,
        });
    },
};
