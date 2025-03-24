<template>
    <div class="d-flex flex-column">
        <div v-if="historiesLoading">正在评估要求...</div>
        <b-modal
            v-else-if="errorMessage"
            id="tour-failed"
            v-model="showModal"
            title="导览失败"
            title-class="h3"
            ok-only>
            {{ errorMessage }}
        </b-modal>
        <b-modal
            v-else-if="loginRequired(currentUser)"
            id="tour-requirement"
            v-model="showModal"
            title="需要登录"
            title-class="h3"
            ok-only>
            您必须登录Galaxy才能使用此导览。
        </b-modal>
        <b-modal
            v-else-if="adminRequired(currentUser)"
            id="tour-requirement"
            v-model="showModal"
            title="需要管理员权限"
            title-class="h3"
            ok-only>
            您必须是管理员用户才能使用此导览。
        </b-modal>
        <b-modal
            v-else-if="newHistoryRequired(currentHistory)"
            id="tour-requirement"
            v-model="showModal"
            title="需要新的历史记录"
            title-class="h3"
            ok-title="创建新的历史记录"
            @ok="createNewHistory()">
            此导览需要在新的历史记录上运行，请在运行前创建新的历史记录。
        </b-modal>
        <TourStep
            v-else-if="currentHistory && currentStep && currentUser"
            :key="currentIndex"
            :step="currentStep"
            :is-playing="isPlaying"
            :is-last="isLast"
            @next="next"
            @end="end"
            @play="play" />
    </div>
</template>

<script>
import { mapActions, mapState } from "pinia";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import TourStep from "./TourStep";

// popup display duration when auto-playing the tour
const playDelay = 3000;

export default {
    components: {
        TourStep,
    },
    props: {
        steps: {
            type: Array,
            required: true,
        },
        requirements: {
            type: Array,
            required: true,
        },
    },
    data() {
        return {
            currentIndex: -1,
            errorMessage: "",
            isPlaying: false,
            showModal: true,
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["currentHistory", "historiesLoading"]),
        currentStep() {
            return this.steps[this.currentIndex];
        },
        numberOfSteps() {
            return this.steps.length;
        },
        isFirst() {
            return this.currentIndex === 0;
        },
        isLast() {
            return this.currentIndex === this.steps.length - 1;
        },
    },
    beforeDestroy() {
        window.removeEventListener("keyup", this.handleKeyup);
    },
    mounted() {
        this.start();
    },
    methods: {
        ...mapActions(useHistoryStore, ["createNewHistory"]),
        start() {
            window.addEventListener("keyup", this.handleKeyup);
            this.currentIndex = 0;
        },
        play(isPlaying) {
            this.isPlaying = isPlaying;
            if (this.isPlaying) {
                this.next();
            }
        },
        loginRequired(user) {
            return this.isFirst && this.requirements.indexOf("logged_in") >= 0 && user.isAnonymous;
        },
        adminRequired(user) {
            return this.isFirst && this.requirements.indexOf("admin") >= 0 && !user.is_admin;
        },
        newHistoryRequired(history) {
            if (this.isFirst) {
                const hasNewHistoryRequirement = this.requirements.indexOf("new_history") >= 0;
                if (!hasNewHistoryRequirement) {
                    return false;
                } else if (history && history.size != 0) {
                    // TODO: better estimate for whether the history is new.
                    return true;
                } else {
                    return false;
                }
            } else {
                return false;
            }
        },
        async next() {
            try {
                // do post-actions
                if (this.currentStep && this.currentStep.onNext) {
                    await this.currentStep.onNext();
                }
                // do pre-actions
                const nextIndex = this.currentIndex + 1;
                if (nextIndex < this.numberOfSteps && this.currentIndex !== -1) {
                    const nextStep = this.steps[nextIndex];
                    if (nextStep.onBefore) {
                        await nextStep.onBefore();
                        // automatically continues to next step if enabled, unless its the last one
                        if (this.isPlaying && nextIndex !== this.numberOfSteps - 1) {
                            setTimeout(() => {
                                if (this.isPlaying) {
                                    this.next();
                                }
                            }, playDelay);
                        }
                    }
                }
                // go to next step
                this.currentIndex = nextIndex;
            } catch (e) {
                this.errorMessage = String(e);
            }
        },
        end() {
            this.currentIndex = -1;
            this.isPlaying = false;
        },
        handleKeyup(e) {
            switch (e.keyCode) {
                case 39:
                    this.next();
                    break;
                case 27:
                    this.end();
                    break;
            }
        },
    },
};
</script>
