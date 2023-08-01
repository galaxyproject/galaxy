<template>
    <b-form :validated="credential.isValid">
        <!-- user label -->
        <GFormGroup label="Description" label-for="credentialDescription" label-cols-lg="3">
            <GInput
                id="credentialDescription"
                v-model="credential.description"
                :state="credential.fieldValid('description')"
                placeholder="Description (optional)"
                trim />
        </GFormGroup>

        <!-- google-openidconnect -->
        <GFormGroup
            v-if="identityProviders.length > 1"
            label="Identity Provider"
            label-for="identityProvider"
            label-cols-lg="3">
            <b-form-select
                id="identityProvider"
                v-model="credential.authn_id"
                :state="credential.fieldValid('authn_id')"
                :options="identityProviders" />
        </GFormGroup>

        <!-- aws/azure, etc -->
        <GFormGroup label="Resource Provider" label-for="resourceProvider" label-cols-lg="3">
            <b-form-select
                id="resourceProvider"
                v-model="credential.resourceProvider"
                :state="credential.fieldValid('provider')"
                :options="resourceProviderOptions" />
        </GFormGroup>

        <CredentialConfig v-model="credential.config" />

        <footer class="border-top">
            <GButton variant="secondary" @click.prevent="$emit('delete', credential)"> Delete Key </GButton>
            <GButton
                aria-label="Save Key"
                :variant="saveButtonVariant"
                :disabled="saveButtonDisabled"
                @click.prevent="$emit('save', credential)">
                {{ saveButtonTitle }}
            </GButton>
        </footer>
    </b-form>
</template>

<script>
import { GButton, GFormGroup, GInput } from "@/component-library";

import CredentialConfig from "./CredentialConfig";
import { Credential, ResourceProviders } from "./model";
import { getIdentityProviders } from "./model/service";

export default {
    components: {
        CredentialConfig,
        GButton,
        GFormGroup,
        GInput,
    },
    props: {
        value: { type: Credential, required: true },
    },
    data() {
        return {
            identityProviders: [],
        };
    },
    computed: {
        credential() {
            return this.value;
        },
        // transformed for bootstrap component
        resourceProviderOptions() {
            return Array.from(ResourceProviders.entries()).map(([value, o]) => ({ value, text: o.label }));
        },
        config() {
            return this.credential.config;
        },
        loading() {
            return this.credential.loading;
        },
        saveButtonDisabled() {
            return !(this.credential.valid && this.credential.dirty);
        },
        saveButtonVariant() {
            return this.saveButtonDisabled ? "secondary" : "primary";
        },
        saveButtonTitle() {
            return this.loading ? "Saving Key..." : "Save Key";
        },
    },
    created() {
        getIdentityProviders().then((result) => {
            if (!this.credential.authn_id && result.length == 1) {
                this.credential.authn_id = result[0].authn_id;
                this.credential.updateState();
            }
            this.identityProviders = result;
        });
    },
};
</script>
