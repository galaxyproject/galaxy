// dependencies
define([], function() {

// tool form templates
return {
    help: function(content) {
        return  '<div class="toolHelp" style="overflow: auto;">' +
                    '<div class="toolHelpBody">' +
                        content +
                    '</div>' +
                '</div>';
    },
    
    success: function(response) {
        // check
        if (!response.jobs || !response.jobs.length) {
            console.debug('tools-template::success() - Failed jobs.');
            return;
        }
       
        // number of jobs
        var njobs = response.jobs.length;
        
        // job count info text
        var njobs_text = '';
        if (njobs == 1) {
            njobs_text = '1 job has';
        } else {
            njobs_text = njobs + ' jobs have';
        }
       
        // create template string
        var tmpl =  '<div class="donemessagelarge">' +
                        '<p>' + njobs_text + ' been successfully added to the queue - resulting in the following datasets:</p>';
        for (var i in response.outputs) {
            tmpl +=     '<p style="padding: 10px 20px;"><b>' + (parseInt(i)+1) + ': ' + response.outputs[i].name + '</b></p>';
        }
        tmpl +=         '<p>You can check the status of queued jobs and view the resulting data by refreshing the History pane. When the job has been run the status will change from \'running\' to \'finished\' if completed successfully or \'error\' if problems were encountered.</p>' +
                    '</div>';
       
        // return success message element
        return tmpl;
    },
    
    error: function(job_def) {
        return  '<div>' +
                    '<p>' +
                        'The server could not complete the request. Please contact the Galaxy Team if this error persists.' +
                    '</p>' +
                    '<textarea class="ui-textarea" disabled style="color: black;" rows="6">' +
                        JSON.stringify(job_def, undefined, 4) +
                    '</textarea>' +
                '</div>';
    },
    
    batchMode: function() {
        return  '<div class="ui-table-form-info">' +
                    '<i class="fa fa-sitemap" style="font-size: 1.2em; padding: 2px 5px;"/>' +
                    'This is a batch mode input field. A separate job will be triggered for each dataset.' +
                '</div>';
    },
    
    requirements: function(options) {
        var requirements_message = 'This tool requires ';
        for (var i in options.requirements) {
            var req = options.requirements[i];
            requirements_message += req.name;
            if (req.version) {
                requirements_message += ' (Version ' + req.version + ')';
            }
            if (i < options.requirements.length - 2) {
                requirements_message += ', ';
            }
            if (i == options.requirements.length - 2) {
                requirements_message += ' and ';
            }
        }
        return requirements_message + '. Click <a target="_blank" href="https://wiki.galaxyproject.org/Tools/Requirements">here</a> for more information.';
    }
};

});