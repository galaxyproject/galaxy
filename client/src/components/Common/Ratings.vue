<template>
    <div>
        <h4>Rating</h4>
        <div>Community ({{ numRatings }} total, {{ aveItemRating.toFixed(1) }} average):</div>
        <star-rating read-only v-model="aveItemRating" :star-size="25" :show-rating="false" />
        <div class="mt-2">Yours:</div>
        <star-rating v-model="currentValue" :star-size="25" :show-rating="false" />
    </div>
</template>
<script>
import StarRating from "vue-star-rating";
import { urlData } from "utils/url";
export default {
    components: {
        StarRating,
    },
    props: {
        aveItemRating: {
            type: Number,
            default: 0,
        },
        userItemRating: {
            type: Number,
            default: 0,
        },
        numRatings: {
            type: Number,
            default: 0,
        },
    },
    computed: {
        currentValue: {
            get() {
                return this.userItemRating;
            },
            set(val) {
                this.$emit("set-rating", val);
            },
        },
    },
};
</script>
