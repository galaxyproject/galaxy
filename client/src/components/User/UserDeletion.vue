<template>
    <b-row class="ml-3 mb-1">
        <i class="pref-icon pt-1 fa fa-lg fa-radiation" />
        <div class="pref-content pr-1">
            <a id="delete-account" href="javascript:void(0)"
                ><b v-b-modal.modal-prevent-closing v-localize>删除账户</b></a
            >
            <div v-localize class="form-text text-muted">删除您在此Galaxy服务器上的账户。</div>
            <b-modal
                id="modal-prevent-closing"
                ref="modal"
                centered
                title="账户删除"
                title-tag="h2"
                @show="resetModal"
                @hidden="resetModal"
                @ok="handleOk">
                <p>
                    <b-alert variant="danger" :show="showDeleteError">{{ deleteError }}</b-alert>
                    <b>
                        此操作无法撤销。您的账户将被永久删除，其中包含的数据也将一并删除。
                    </b>
                </p>
                <b-form ref="form" @submit.prevent="handleSubmit">
                    <b-form-group
                        :state="nameState"
                        label="请输入您的账户邮箱作为确认。"
                        label-for="Email"
                        invalid-feedback="邮箱不正确">
                        <b-form-input id="name-input" v-model="name" :state="nameState" required></b-form-input>
                    </b-form-group>
                </b-form>
            </b-modal>
        </div>
    </b-row>
</template>

<script>
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import { userLogoutClient } from "utils/logout";
import { withPrefix } from "utils/redirect";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    props: {
        userId: {
            type: String,
            required: true,
        },
        email: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            name: "",
            nameState: null,
            deleteError: "",
        };
    },
    computed: {
        showDeleteError() {
            return this.deleteError !== "";
        },
    },
    methods: {
        checkFormValidity() {
            const valid = this.$refs.form.checkValidity();
            this.nameState = valid;
            return valid;
        },
        resetModal() {
            this.name = "";
            this.nameState = null;
        },
        handleOk(bvModalEvt) {
            // Prevent modal from closing
            bvModalEvt.preventDefault();
            // Trigger submit handler
            this.handleSubmit();
        },
        async handleSubmit() {
            if (!this.checkFormValidity()) {
                return false;
            }
            if (this.email === this.name) {
                this.nameState = true;
                try {
                    await axios.delete(withPrefix(`/api/users/${this.userId}`));
                } catch (e) {
                    if (e.response.status === 403) {
                        this.deleteError =
                            "此实例必须配置用户删除功能才能允许用户自行删除。请联系管理员寻求帮助。";
                        return false;
                    }
                }
                userLogoutClient();
            } else {
                this.nameState = false;
                return false;
            }
        },
    },
};
</script>

<style scoped>
@import "user-styles.scss";
</style>
