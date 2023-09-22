<!-- container for an uploadBox -->
<template>
    <div :class="wrapperClass">
        <div class="upload-top">
            <div class="upload-top-info" v-html="topInfo"></div>
        </div>
        <div ref="uploadBox" class="upload-box" :style="boxStyle" :class="{ highlight: highlightBox }">
            <slot />
        </div>
        <div v-if="hasFooter" class="upload-footer">
            <slot name="footer" />
        </div>
        <div v-else class="clear" />
        <div class="upload-buttons">
            <slot name="buttons" />
        </div>
    </div>
</template>

<script>
export default {
    props: {
        topInfo: {
            type: String,
            default: "&nbsp;",
        },
        wrapperClass: {
            type: String,
            default: "upload-view-default",
        },
        highlightBox: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        hasFooter() {
            // https://stackoverflow.com/questions/44077277/only-show-slot-if-it-has-content/50096300#50096300
            const name = "footer";
            return !!this.$slots[name] || !!this.$scopedSlots[name];
        },
        boxStyle: function () {
            return {
                height: this.hasFooter ? "300px" : "335px",
            };
        },
    },
};
</script>
