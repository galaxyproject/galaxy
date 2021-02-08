// Mixin with focus-hilight dom stuff

export default {
    data: () => ({
        suppressFocus: false,
    }),
    methods: {
        setFocus(index) {
            if (this.suppressFocus) return;
            const ul = this.$el.closest(".scroller");
            const el = ul.querySelector(`[tabindex="${index}"]`);
            if (el) el.focus();
        },
    },
    created() {
        this.$root.$on("bv::dropdown::show", () => (this.suppressFocus = true));
        this.$root.$on("bv::dropdown::hide", () => (this.suppressFocus = false));
    },
};
