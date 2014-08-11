define([
    "mvc/base-mvc",
    "mvc/citation/citation-model",
    "utils/localization"
], function( baseMVC, citationModel, _l ){

var CitationView = Backbone.View.extend({
    tagName: 'div',
    className: 'citations',
    render: function() {
        this.$el.append( "<p>" + this.formattedReference() + "</p>" );
        return this;
    },
    formattedReference: function() {
        var model = this.model;
        var entryType = model.entryType();
        var fields = model.fields();

        var ref = "";
        // Code inspired by...
        // https://github.com/vkaravir/bib-publication-list/blob/master/src/bib-publication-list.js
        var authorsAndYear = this._asSentence( (fields.author ? fields.author : "") + (fields.year ? (" (" + fields.year + ")") : "") ) + " ";
        var title = fields.title || "";
        var pages = fields.pages ? ("pp. " + fields.pages) : "";
        var address = fields.address;
        if( entryType == "article" ) {
            ref = authorsAndYear + this._asSentence(title) +
                    (fields.journal ? ("In <em>" + fields.journal + ", ") : "") +
                    (fields.volume ? fields.volume : "") +
                    (fields.number ? ( "(" + fields.number + "), " ) : ", " ) +
                    this._asSentence(pages) +
                    this._asSentence(fields.address) +
                    "<\/em>";
        } else if( entryType == "inproceedings" || entryType == "proceedings" ) {
            ref = authorsAndYear + 
                    this._asSentence(title) + 
                    (fields.booktitle ? ("In <em>" + fields.booktitle + ", ") : "") +
                    (pages ? pages : "") +
                    (address ? ", " + address : "") + 
                    ".<\/em>";
        } else if( entryType == "mastersthesis" || entryType == "phdthesis" ) {
            ref = authorsAndYear + this._asSentence(title) +
                    (fields.howpublished ? fields.howpublished + ". " : "") +
                    (fields.note ? fields.note + "." : "");
        } else if( entryType == "techreport" ) {
            ref = authorsAndYear + ". " + this._asSentence(title) +
                    this._asSentence(fields.institution) +
                    this._asSentence(fields.number) +
                    this._asSentence(fields.type);
        } else if( entryType == "book" || entryType == "inbook" || entryType == "incollection" ) {
            ref = this._asSentence(authorsAndYear) + " " + this._formatBookInfo(fields);
        } else {
            ref = this._asSentence(authorsAndYear) + " " + this._asSentence(title) +
                    this._asSentence(fields.howpublished) +
                    this._asSentence(fields.note);
        }
        var doiUrl = "";
        if( fields.doi ) {
            doiUrl = 'http://dx.doi.org/' + fields.doi;
            ref += '[<a href="' + doiUrl + '">doi:' + fields.doi + "</a>]";
        }
        var url = fields.url || doiUrl;
        if( url ) {
            ref += '[<a href="' + url + '">Link</a>]';
        }
        return ref;
    },
    _formatBookInfo: function(fields) {
        var info = "";
        if( fields.chapter ) {
            info += fields.chapter + " in ";
        }
        if( fields.title ) {
            info += "<em>" + fields.title + "<\/em>";
        }
        if( fields.editor ) {
            info += ", Edited by " + fields.editor + ", ";
        }
        if( fields.publisher) {
            info += ", " + fields.publisher;
        }
        if( fields.pages ) {
            info += ", pp. " + fields.pages + "";
        }
        if( fields.series ) {
            info += ", <em>" + fields.series + "<\/em>";
        }
        if( fields.volume ) {
            info += ", Vol." + fields.volume;
        }
        if( fields.issn ) {
            info += ", ISBN: " + fields.issn;
        }
        return info + ".";
    },
    _asSentence: function(str) {
        return (str && str.trim()) ? str + ". " : "";
    }
});

var CitationListView = Backbone.View.extend({
    el: '#citations',
    /**
     * Set up view.
     */
    initialize: function() {
        this.listenTo( this.collection, 'add', this.renderCitation );
    },

    events: {
        'click .citations-to-bibtex': 'showBibtex',
        'click .citations-to-formatted': 'showFormatted'
    },

    renderCitation: function( citation ) {
        var citationView = new CitationView( { model: citation } );
        this.$(".citations-formatted").append( citationView.render().el );
        var rawTextarea = this.$(".citations-bibtex-text");
        rawTextarea.val( rawTextarea.val() + "\n\r" + citation.attributes.content );
    },

    render: function() {
        this.$el.html(this.citationsElement());
        this.collection.each(function( item ){
            this.renderCitation( item );
        }, this);
        this.showFormatted();
    },

    showBibtex: function() {
        this.$(".citations-to-formatted").show();
        this.$(".citations-to-bibtex").hide();
        this.$(".citations-bibtex").show();
        this.$(".citations-formatted").hide();
        this.$(".citations-bibtex-text").select();
    },

    showFormatted: function() {
        this.$(".citations-to-formatted").hide();
        this.$(".citations-to-bibtex").show();
        this.$(".citations-bibtex").hide();
        this.$(".citations-formatted").show();
    },

    partialWarningElement: function() {
        if( this.collection.partial ) {
            return [
                '<div style="padding:5px 10px">',
                '<b>Warning: This is a experimental feature.</b> Most Galaxy tools will not annotate',
                ' citations explicitly at this time. When writing up your analysis, please manually',
                ' review your histories and find all references',
                ' that should be cited in order to completely describe your work. Also, please remember to',
                ' <a href="https://wiki.galaxyproject.org/CitingGalaxy">cite Galaxy</a>.',
                '</div>',
            ].join('');
        } else {
            return '';
        }
    },

    citationsElement: function() {
        return [
            '<div class="toolForm">',
                '<div class="toolFormTitle">',
                    _l("Citations"),
                    ' <i class="fa fa-pencil-square-o citations-to-bibtex" title="Select all as BibTeX."></i>',
                    ' <i class="fa fa-times citations-to-formatted" title="Return to formatted citation list."></i>',
                '</div>',
                '<div class="toolFormBody" style="padding:5px 10px">',
                this.partialWarningElement(),
                '<span class="citations-formatted"></span>',
                '</div>',
                '<div class="citations-bibtex toolFormBody" style="padding:5px 10px">',
                '<textarea style="width: 100%; height: 500px;" class="citations-bibtex-text"></textarea>',
                '</div>',
            '</div>'
        ].join( '' );
    }
});

//==============================================================================
return {
    CitationView : CitationView,
    CitationListView  : CitationListView
};

});