const watchChangeHandler = (label) => (newVal, oldVal) => {
    if (newVal != oldVal) {
        console.log(label, newVal);
    }
};

export default {
    watch: {
        items: {
            immediate: true,
            handler: watchChangeHandler("PROP: items"),
        },

        itemHeight: {
            immediate: true,
            handler: watchChangeHandler("PROP: itemHeight"),
        },

        scrollStartKey: {
            immediate: true,
            handler: watchChangeHandler("PROP: scrollStartKey"),
        },

        topPlaceholders: {
            immediate: true,
            handler: watchChangeHandler("PROP: topPlaceholders"),
        },

        bottomPlaceholders: {
            immediate: true,
            handler: watchChangeHandler("PROP: bottomPlaceholders"),
        },

        scrollTop: {
            immediate: true,
            handler: watchChangeHandler("DATA: scrollTop"),
        },

        scrollerHeight: {
            immediate: true,
            handler: watchChangeHandler("DATA: scrollerHeight"),
        },

        topPlaceholderHeight: {
            immediate: true,
            handler: watchChangeHandler("COMPUTED: topPlaceholderHeight"),
        },

        bottomPlaceholderHeight: {
            immediate: true,
            handler: watchChangeHandler("COMPUTED: bottomPlaceholderHeight"),
        },

        contentHeight: {
            immediate: true,
            handler: watchChangeHandler("DATA: contentHeight"),
        },
    },
};
