<template>
    <div
        ref="tour-element"
        class="tour-element"
        :class="{ 'tour-element-sticky': !targetElement, 'tour-has-title': !!step.title }">
        <div v-if="step.title" class="tour-header">
            <div class="tour-title" v-html="step.title"></div>
        </div>
        <div v-if="step.content" class="tour-content" v-html="step.content" />
        <div class="tour-buttons">
            <div v-if="isLast">
                <button class="tour-button tour-end" @click.prevent="$emit('end')">关闭</button>
            </div>
            <div v-else-if="isPlaying">
                <button class="tour-button tour-stop" @click.prevent="$emit('play', false)">停止</button>
            </div>
            <div v-else>
                <button class="tour-button tour-end" @click.prevent="$emit('end')">取消</button>
                <button class="tour-button tour-play" @click.prevent="$emit('play', true)">播放</button>
                <button class="tour-button tour-next" @click.prevent="$emit('next')">继续</button>
            </div>
        </div>
        <div v-if="targetElement" class="tour-arrow" data-popper-arrow />
    </div>
</template>

<script>
import { createPopper } from "@popperjs/core";

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
    computed: {
        targetElement() {
            if (this.step.element) {
                return document.querySelector(this.step.element);
            }
            return null;
        },
    },
    mounted() {
        this.createStep();
    },
    methods: {
        createStep() {
            if (this.targetElement) {
                createPopper(this.targetElement, this.$refs["tour-element"], {
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
};
</script>
