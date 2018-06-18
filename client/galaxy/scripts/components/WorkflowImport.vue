<template>
    <div class="ui-portlet-limited">
        <div class="portlet-header">
            <div class="portlet-title">
                <i class="portlet-title-icon fa fa-upload"></i>
                <span class="portlet-title-text"><b>Import Workflow</b></span>
            </div>
        </div>
        <div class="portlet-content">
            <div v-if="errormessage" class="ui-message alert alert-danger">
                {{ errormessage }}
            </div>
            <div class="portlet-body">
                <form ref="form">
                    <div class="ui-form-element">
                        <div class="ui-form-title">Archived Workflow URL</div>
                        <input class="ui-input" type="text" name="archive_source"/>
                        <div class="ui-form-info">If the workflow is accessible via a URL, enter the URL above and click Import.</div>
                    </div>
                    <div class="ui-form-element">
                        <div class="ui-form-title">Archived Workflow file</div>
                        <input type="file" name="archive_file"/>
                        <div class="ui-form-info">If the workflow is in a file on your computer, choose it and then click Import.</div>
                    </div>
                </form>
            </div>
            <div class="portlet-buttons">
                <input class="btn btn-primary" type="button" value="Import Workflow" @click="submit"/>
            </div>
        <hr/>
        <div class="ui-form-element">
            <div class="ui-form-title">Import a Workflow from myExperiment</div>
            <a :href=myexperiment_target_url>Visit myExperiment</a>
            <div class="ui-form-info">Click the link above to visit myExperiment and search for Galaxy workflows.</div>
        </div>
        </div>
    </div>
</template>
<script>
export default {
    data() {
        return {
            errormessage: null,
            myexperiment_target_url: `http://${Galaxy.config.myexperiment_target_url}/galaxy?galaxy_url=${
                window.location.protocol
            }//${window.location.host}`
        };
    },
    methods: {
        submit: function() {
            $.ajax({
                url: `${Galaxy.root}api/workflows`,
                data: new FormData(this.$refs.form),
                cache: false,
                contentType: false,
                processData: false,
                method: "POST"
            })
                .done(response => {
                    window.location = `${Galaxy.root}workflows/list?message=${response.message}&status=${
                        response.status
                    }`;
                })
                .fail(response => {
                    let message = response.responseJSON && response.responseJSON.err_msg;
                    this.errormessage = message || "Import failed for unkown reason.";
                });
        }
    }
};
</script>
<style>
.ui-message {
    display: block;
}
</style>
