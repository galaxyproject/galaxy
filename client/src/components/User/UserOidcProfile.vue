<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faUser } from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

const { config, isConfigLoaded } = useConfig(true);

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const breadcrumbItems = computed(() => [{ title: "User Preferences", to: "/user" }, { title: "Manage Profile" }]);

const username = computed(() => currentUser.value?.username || localize("Not available"));
const email = computed(() => currentUser.value?.email || localize("Not available"));
const profileUrl = computed(() => {
    if (!isConfigLoaded.value) {
        // Need to return a value to ensure the GButton is
        // rendered as a link
        return "#";
    }
    return config.value.oidc_profile_url || "";
});
const profileButtonLabel = computed(() => {
    const providers = Object.keys(config.value.oidc) || [];
    if (providers.length === 0 || providers === null) {
        return null;
    }
    const providerConfig = config.value.oidc[providers[0]!];
    const providerLabel = providerConfig.custom_button_text || providerConfig.label;
    if (providerLabel) {
        return `Update profile details at ${providerLabel}`;
    }
    return "Update profile details";
});

const buttonDisabled = computed(() => !isConfigLoaded.value || !profileUrl.value);
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />
        <div id="manage-profile-card" class="ui-portlet-section">
            <div class="portlet-header">
                <span class="portlet-title">
                    <FontAwesomeIcon :icon="faUser" fixed-width class="mr-1" />
                    <span class="portlet-title-text">{{ localize("Manage Profile") }}</span>
                </span>
            </div>
            <div class="portlet-content">
                <dl class="d-flex flex-column flex-gapy-1">
                    <div class="my-2">
                        <dt class="text-md-left">{{ localize("Email") }}</dt>
                        <dd>{{ email }}</dd>
                    </div>
                    <div class="my-2">
                        <dt class="text-md-left">{{ localize("Username") }}</dt>
                        <dd>{{ username }}</dd>
                        <span class="text-sm-left">
                            <em>
                                {{
                                    localize(
                                        "Your username is an identifier that will be used to generate addresses for information you share publicly."
                                    )
                                }}
                            </em>
                        </span>
                    </div>
                    <div class="my-2">
                        <dt>{{ localize("Password") }}</dt>
                        <dd>●●●●●●●●●●</dd>
                    </div>
                </dl>

                <GButton
                    color="blue"
                    size="medium"
                    class="mt-3"
                    :disabled="buttonDisabled"
                    :href="profileUrl"
                    target="_blank">
                    <span>{{ localize(profileButtonLabel) }}</span>
                    <span class="mr-1 fa fa-external-link-alt" />
                </GButton>
            </div>
        </div>
    </div>
</template>
