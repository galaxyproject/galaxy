export default {
    props: {
        threshold: {
            type: [Array, Number],
            required: false,
            default: () => [0.5],
        },
        root: {
            type: HTMLElement,
            required: false,
            default: () => null,
        },
        rootMargin: {
            type: String,
            required: false,
            default: () => "0px 0px 0px 0px",
        },
    },
    methods: {
        handler(entries) {
            entries.forEach((entry) => {
                const { isIntersecting, target } = entry;
                const key = this.elemToKey.get(target);
                const evtName = isIntersecting ? "enter" : "leave";
                this.$emit(evtName, key, entry);
            });
        },
        getCurrentVnodes() {
            let vnodes = [];
            try {
                const rawNodes = this.$slots.default[0].componentOptions.children;
                vnodes = rawNodes.filter((node) => node.tag);
            } catch (err) {
                console.warn("Nothing in slots?", err);
                throw err;
            }
            return vnodes;
        },
        registerObservers(vnodes) {
            vnodes.forEach(({ key, elm }) => {
                this.observer.observe(elm);
                this.elemToKey.set(elm, key);
            });
        },
        cleanupObservers(vnodes) {
            const newElements = vnodes.reduce((result, vnode) => {
                return result.add(vnode.elm);
            }, new Set());

            const currentStuff = Array.from(this.elemToKey.entries());
            currentStuff.forEach(([el, key]) => {
                if (!newElements.has(el)) {
                    this.observer.unobserve(el);
                    this.$emit("destroy", key);
                    this.elemToKey.delete(el);
                }
            });
        },
    },
    mounted() {
        this.elemToKey = new Map();
        const { threshold, root, rootMargin } = this;
        this.observer = new IntersectionObserver(this.handler, { threshold, root, rootMargin });
        const vnodes = this.getCurrentVnodes();
        this.registerObservers(vnodes);
    },
    updated() {
        const vnodes = this.getCurrentVnodes();
        this.cleanupObservers(vnodes);
        this.registerObservers(vnodes);
    },
    beforeDestroy() {
        this.observer.disconnect();
    },
    render() {
        return this.$slots.default;
    },
};
