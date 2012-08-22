/*
TODO: 
    as always: where does the model end and the view begin?
    HistoryPanel
    HistoryCollection: (collection of histories: 'Saved Histories')
    
CASES:
    logged-in/NOT
*/
//==============================================================================
var HistoryItem = BaseModel.extend({
    // a single history structure
    // from: http://localhost:8080/api/histories/f2db41e1fa331b3e/contents/f2db41e1fa331b3e
    /*
    {
        "data_type": "fastq", 
        "deleted": false, 
        "download_url": "/datasets/f2db41e1fa331b3e/display?to_ext=fastq", 
        "file_size": 226297533, 
        "genome_build": "?", 
        "id": "f2db41e1fa331b3e", 
        "metadata_data_lines": null, 
        "metadata_dbkey": "?", 
        "metadata_sequences": null, 
        "misc_blurb": "215.8 MB", 
        "misc_info": "uploaded fastq file", 
        "model_class": "HistoryDatasetAssociation", 
        "name": "LTCF-2-19_GTGAAA_L001_R1_001.fastq", 
        "state": "ok", 
        "visible": true
    }
    */
    
    display     : function(){},
    edit_attr   : function(){},
    remove      : function(){},
    download    : function(){},
    details     : function(){},
    rerun       : function(){},
    tags        : function(){},
    annotations : function(){},
    peek        : function(){}
});

//..............................................................................
var HistoryItemView = BaseView.extend({
    // view for History model used in HistoryPanelView
    tagName     : "div",
    className   : "historyItemContainer",
    
    icons       : {
        display     : 'path to icon',
        edit_attr   : 'path to icon',
        remove      : 'path to icon',
        download    : 'path to icon',
        details     : 'path to icon',
        rerun       : 'path to icon',
        tags        : 'path to icon',
        annotations : 'path to icon'
    },
    
    render      : function(){
        this.$el.append( 'div' );
    }
    
});



//==============================================================================
var History = Backbone.Collection.extend({
    // a collection of HistoryItems
    
    // from: http://localhost:8080/api/histories/f2db41e1fa331b3e
    /*
    {
        "contents_url": "/api/histories/f2db41e1fa331b3e/contents", 
        "id": "f2db41e1fa331b3e", 
        "name": "one", 
        "state": "ok", 
        "state_details": {
            "discarded": 0, 
            "empty": 0, 
            "error": 0, 
            "failed_metadata": 0, 
            "new": 0, 
            "ok": 4, 
            "queued": 0, 
            "running": 0, 
            "setting_metadata": 0, 
            "upload": 0
        }
    }
    */
    
    // from: http://localhost:8080/api/histories/f2db41e1fa331b3e/contents
    // (most are replicated in HistoryItem)
    /*
    [
        {
            "id": "f2db41e1fa331b3e", 
            "name": "LTCF-2-19_GTGAAA_L001_R1_001.fastq", 
            "type": "file", 
            "url": "/api/histories/f2db41e1fa331b3e/contents/f2db41e1fa331b3e"
        }, 
        {
            "id": "f597429621d6eb2b", 
            "name": "LTCF-2-19_GTGAAA_L001_R2_001.fastq", 
            "type": "file", 
            "url": "/api/histories/f2db41e1fa331b3e/contents/f597429621d6eb2b"
        }, 
        {
            "id": "1cd8e2f6b131e891", 
            "name": "FASTQ Groomer on data 1", 
            "type": "file", 
            "url": "/api/histories/f2db41e1fa331b3e/contents/1cd8e2f6b131e891"
        }, 
        {
            "id": "ebfb8f50c6abde6d", 
            "name": "FASTQ Groomer on data 2", 
            "type": "file", 
            "url": "/api/histories/f2db41e1fa331b3e/contents/ebfb8f50c6abde6d"
        }, 
        {
            "id": "33b43b4e7093c91f", 
            "name": "Sa.04-02981.fasta", 
            "type": "file", 
            "url": "/api/histories/f2db41e1fa331b3e/contents/33b43b4e7093c91f"
        }
    ]
    */
});

//..............................................................................
var HistoryCollectionView = BaseView.extend({
    // view for the HistoryCollection (as per current right hand panel)
    tagName     : "body",
    className   : "historyCollection",
    
    render      : function(){
        
    }
    
});

