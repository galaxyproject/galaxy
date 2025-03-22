<template>
    <section class="external-id">
        <b-alert :show="!!connectExternal" variant="info">
            您已登录。现在可以将电子邮箱为 <i>{{ userEmail }}</i> 的Galaxy用户账户与您首选的外部提供商关联。
        </b-alert>
        <b-alert :show="!!existingEmail" variant="warning">
            注意：我们发现一个与此身份邮箱 <i>{{ existingEmail }}</i> 匹配的Galaxy账户。当前账户 <i>{{ userEmail }}</i> 已关联到此外部身份。如果您希望将此身份关联到其他账户，需要先将其与当前账户断开连接。
        </b-alert>
        <header>
            <b-alert
                dismissible
                fade
                variant="warning"
                :show="errorMessage !== null"
                @dismissed="errorMessage = null"
                >{{ errorMessage }}</b-alert
            >

            <hgroup class="external-id-title">
                <h1 class="h-lg">管理外部身份</h1>
            </hgroup>

            <p>
                拥有现有Galaxy用户账户（如通过Galaxy用户名和密码创建）的用户可以将其账户与第三方身份关联。例如，如果用户将其Galaxy账户与Google账户关联，那么他们可以使用Galaxy用户名和密码登录，也可以使用Google账户登录。无论使用哪种方法，他们都将使用相同的Galaxy用户账户，因此可以访问相同的历史记录、工作流、数据集、库等。
            </p>

            <p>
                查看更多信息，包括支持的身份提供商列表，请点击<a href="https://galaxyproject.org/authnz/use/oidc/">这里</a>。
            </p>
        </header>

        <div v-if="items.length" class="external-subheading">
            <h2 class="h-md">已连接的外部身份</h2>
            <b-button
                v-for="item in items"
                :key="item.email"
                aria-label="断开外部身份连接"
                title="断开外部身份连接"
                class="d-block mt-3"
                @click="onDisconnect(item)">
                断开连接 {{ capitalizeAsTitle(item.provider_label) }} -
                {{ item.email }}
            </b-button>

            <b-modal
                id="disconnectIDModal"
                ref="deleteModal"
                centered
                title="断开身份连接？"
                size="sm"
                @ok="disconnectID"
                @cancel="doomedItem = null"></b-modal>

            <b-modal
                id="disconnectAndResetModal"
                ref="deleteAndResetModal"
                centered
                title="删除最后一个外部身份"
                @ok="disconnectAndReset"
                @cancel="doomedItem = null">
                <p>
                    这是您唯一定义的外部身份。如果删除此身份，您将被登出。要重新登录，您需要使用与账户关联的密码，或重新连接到此第三方身份。如果您不知道Galaxy用户密码，可以重置密码或联系管理员寻求帮助。
                </p>
            </b-modal>

            <b-alert
                dismissible
                fade
                variant="warning"
                :show="errorMessage !== null"
                @dismissed="errorMessage = null"
                >{{ errorMessage }}</b-alert
            >
        </div>

        <div v-if="enable_oidc" class="external-subheading">
            <h2 class="h-md">连接其他外部身份</h2>
            <ExternalLogin />
        </div>
    </section>
</template>

<script>
import { getGalaxyInstance } from "app";
import BootstrapVue from "bootstrap-vue";
import { Toast } from "composables/toast";
import { sanitize } from "dompurify";
import { userLogout } from "utils/logout";
import Vue from "vue";

import { capitalizeFirstLetter } from "@/utils/strings";

import svc from "./service";

import ExternalLogin from "components/User/ExternalIdentities/ExternalLogin.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        ExternalLogin,
    },
    data() {
        const galaxy = getGalaxyInstance();
        return {
            items: [],
            showHelp: true,
            loading: false,
            doomedItem: null,
            errorMessage: null,
            enable_oidc: galaxy.config.enable_oidc,
            cilogonOrCustos: null,
            userEmail: galaxy.user.get("email"),
        };
    },
    computed: {
        connectExternal() {
            var urlParams = new URLSearchParams(window.location.search);
            return urlParams.has("connect_external") && urlParams.get("connect_external") == "true";
        },
        deleteButtonVariant() {
            return this.showDeleted ? "primary" : "secondary";
        },
        existingEmail() {
            var urlParams = new URLSearchParams(window.location.search);
            return urlParams.get("email_exists");
        },
        hasDoomed: {
            get() {
                return this.doomedItem !== null;
            },
            // This setter is here because vue-bootstrap modal
            // tries to set this property for unfathomable reasons
            set() {},
        },
    },
    watch: {
        showDeleted(deleted) {
            this.loadIdentities({ deleted });
        },
    },
    created() {
        this.loadIdentities();
    },
    mounted() {
        const params = new URLSearchParams(window.location.search);
        const notificationMessage = sanitize(params.get("notification"));
        Toast.success(notificationMessage);
    },
    methods: {
        capitalizeAsTitle(str) {
            return capitalizeFirstLetter(str);
        },
        loadIdentities() {
            this.loading = true;
            svc.getIdentityProviders()
                .then((results) => {
                    this.items = results;
                })
                .catch(this.setError("无法加载已连接的外部身份。"))
                .finally(() => (this.loading = false));
        },
        onDisconnect(doomed) {
            this.doomedItem = doomed;
            if (doomed.id) {
                if (this.items.length > 1) {
                    // User must confirm that they want to disconnect the identity
                    this.$refs.deleteModal.show();
                } else {
                    // User is notified to reset password to use regular Galaxy login and avoid lockout
                    this.$refs.deleteAndResetModal.show();
                    this.setError(
                        "在断开此身份连接之前，您需要设置账户密码，以避免被锁定在账户之外。"
                    );
                }
            } else {
                this.setError(
                    "在断开此身份连接之前，您需要设置账户密码，以避免被锁定在账户之外。"
                );
            }
        },
        disconnectID() {
            // Called when the modal is closed with an "OK"
            svc.disconnectIdentity(this.doomedItem)
                .then(() => {
                    this.removeItem(this.doomedItem);
                })
                .catch((error) => {
                    if (error.data) {
                        this.setError("无法断开外部身份连接。");
                    } else {
                        this.removeItem(this.doomedItem);
                    }
                })
                .finally(() => {
                    this.removeItem(this.doomedItem);
                    this.doomedItem = null;
                });
        },
        disconnectAndReset() {
            // Disconnects the user's final ext id and logouts of current session
            this.disconnectID();
            userLogout();
        },
        removeItem(item) {
            this.items = this.items.filter((o) => o != item);
        },
        setError(msg) {
            return (err) => {
                this.errorMessage = msg;
                console.warn(err);
            };
        },
    },
};
</script>

<style lang="scss">
@import "~bootstrap/scss/functions";
@import "~bootstrap/scss/variables";
@import "~bootstrap/scss/mixins";
@import "~bootstrap/scss/utilities/spacing";
@import "scss/theme/blue.scss";
@import "scss/mixins";

.operations {
    margin-bottom: 0;

    ul {
        @include list_reset();
        display: flex;
        li:not(:first-child) {
            @extend .ml-2;
        }
    }
}

// General Layout

.external-id {
    // header sticks, bottom part scrolls
    @include scrollingListLayout("header", ".scroll-container");

    // title left, icons right
    .external-id-title {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;

        // top icon menu
        .operations {
            li {
                a,
                a::before {
                    font-size: 1rem;
                    color: $gray-400;
                }
                a.active::before,
                a:hover::before {
                    color: $brand-primary;
                }
            }
        }
    }
    .external-subheading {
        margin-top: 1rem;
    }
}

// Single list item

.external-id-key {
    header hgroup {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        user-select: none;

        > * {
            margin-bottom: 0;
        }
    }

    form {
        @extend .my-3;
        @extend .pt-3;
        // removes weird double arrows on select
        .custom-select {
            background: none;
        }
        // Allow side-by-side labels to work
        .form-row {
            display: flex;
            input,
            select {
                max-width: none;
            }
            label {
                font-weight: 400;
            }
        }

        // button list at bottom of form
        footer {
            display: flex;
            flex-direction: row;
            justify-content: flex-end;
            @extend .pt-3;

            button:not(:first-child) {
                @extend .ml-1;
            }
        }
    }

    // icon menu
    .operations {
        list-style-type: none;

        .delete a,
        button {
            @include fontawesome($fa-var-times);
        }
    }
}

// Transitions
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.5s;
}

.fade-enter,
.fade-leave-to {
    opacity: 0;
}

// Delete modal
#disconnectIDModal {
    .modal-body {
        display: none;
    }
    .modal-dialog {
        max-width: 300px;
    }
}
</style>
