<template>
    <b-modal v-bind="$attrs" :title="title" title-tag="h2" v-on="$listeners">
        <transition name="fade">
            <b-alert v-localize :show="currentUser.isAnonymous" variant="warning">
                As an anonymous user, unless you login or register, you will lose your current history after copying
                this history. You can <a href="/user/login">log in here</a> or <a href="/user/create">register here</a>.
            </b-alert>
        </transition>

        <transition name="fade">
            <div v-if="loading" class="d-flex justify-content-center mb-3">
                <b-spinner label="Copying History..."></b-spinner>
            </div>
        </transition>

        <transition>
            <b-form v-if="!loading">
                <b-form-group label="Enter a title for the new history" label-for="copy-modal-title">
                    <b-input id="copy-modal-title" v-model="name" :state="newNameValid" required />
                    <b-form-invalid-feedback :state="newNameValid">
                        Please enter a valid history title.
                    </b-form-invalid-feedback>
                </b-form-group>

                <b-form-group label="Choose which datasets from the original history to include.">
                    <b-form-radio v-model="copyAll" :value="false">
                        Copy only the active, non-deleted datasets.
                    </b-form-radio>
                    <b-form-radio v-model="copyAll" :value="true">
                        Copy all datasets including deleted ones.
                    </b-form-radio>
                </b-form-group>
            </b-form>
        </transition>

        <div slot="modal-footer" slot-scope="{ ok, cancel }">
            <div>
                <b-button class="mr-3" @click="cancel()"> Cancel </b-button>
                <b-button :variant="saveVariant" :disabled="!formValid" @click="copy(ok)">
                    {{ saveTitle | localize }}
                </b-button>
            </div>
        </div>
    </b-modal>
</template>

<script>
import { mapActions, mapGetters } from "vuex";

export default {
    props: {
        history: { type: Object, required: true },
    },
    data() {
        return {
            name: "",
            copyAll: false,
            loading: false,
        };
    },
    computed: {
        ...mapGetters("user", ["currentUser"]),

        title() {
            return `Copying History: ${this.history.name}`;
        },
        saveTitle() {
            return this.loading ? "Saving..." : "Copy History";
        },
        saveVariant() {
            return this.loading ? "info" : this.formValid ? "primary" : "secondary";
        },
        newNameValid() {
            if (this.name == this.history.name) {
                return null;
            }
            return this.name.length > 0;
        },
        formValid() {
            return this.newNameValid;
        },
    },
    watch: {
        history: {
            handler(newHistory) {
                this.name = `Copy of '${newHistory.name}'`;
            },
            immediate: true,
        },
    },
    methods: {
        ...mapActions("history", ["copyHistory"]),

        async copy(close) {
            this.loading = true;
            const { history, name, copyAll } = this;
            await this.copyHistory({ history, name, copyAll });
            this.loading = false;
            close();
        },
    },
};
</script>

<style lang="scss">
@import "scss/transitions.scss";
</style>
