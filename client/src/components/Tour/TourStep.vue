<template>
    <div
        class="tour-element"
        :class="{ 'tour-element-sticky': !targetElement, 'tour-has-title': !!step.title }"
        :id="'tour-element-' + hash"
        :ref="'tour-element-' + hash">
        <div v-if="step.title" class="tour-header">
            <div class="tour-title" v-html="step.title"></div>
        </div>
        <div v-if="step.content" class="tour-content" v-html="step.content" />
        <div class="tour-buttons">
            <div v-if="isLast">
                <button class="tour-button tour-end" @click.prevent="$emit('end')">Close</button>
            </div>
            <div v-else-if="isPlaying">
                <button class="tour-button tour-stop" @click.prevent="$emit('play', false)">Stop</button>
            </div>
            <div v-else>
                <button class="tour-button tour-end" @click.prevent="$emit('end')">Cancel</button>
                <button class="tour-button tour-play" @click.prevent="$emit('play', true)">Play</button>
                <button class="tour-button tour-next" @click.prevent="$emit('next')">Continue</button>
            </div>
        </div>
        <div v-if="targetElement" class="tour-arrow" data-popper-arrow />
    </div>
</template>

<script>
import { createPopper } from "@popperjs/core";
import sum from "hash-sum";

export default {
    props: {
        step: {
            type: Object,
        },
        isPlaying: {
            type: Boolean,
        },
        isLast: {
            type: Boolean,
        },
    },
    data() {
        return {
            hash: sum(this.step.target),
            targetElement: document.querySelector(this.step.target),
        };
    },
    methods: {
        createStep() {
            if (this.targetElement) {
                this.targetElement.scrollIntoView({ behavior: "smooth" });
                createPopper(this.targetElement, this.$refs["tour-element-" + this.hash], {
                    modifiers: [
                        {
                            name: "preventOverflow",
                            options: {
                                altAxis: true,
                                tether: false,
                                padding: 20,
                            },
                        },
                    ],
                    strategy: "absolute",
                    placement: "auto",
                });
            }
        },
    },
    mounted() {
        this.createStep();
    },
};
</script>
