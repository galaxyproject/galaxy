/*==============================================================================
Backbone MV for Tags


TODO:
move rendering from tagging_common.py
move functionality from controllers/tag.py
?? - polymorph on class or simply class as attr?

==============================================================================*/
/** Single Tag model
 */
var Tag = BaseModel.extend( LoggableMixin ).extend({
    
    // uncomment this out see log messages
    logger              : console,
    
    defaults : {
        id : null,
        itemClass : null
    },
     
    toString : function(){
        return 'Tag()';
    }
});

//------------------------------------------------------------------------------
/** Single Tag view
 */
var TagView = BaseView.extend( LoggableMixin ).extend({
    
    // uncomment this out see log messages
    logger              : console,

    toString : function(){
        return 'TagView()';
    }
});

//==============================================================================
/** A collection of Tags
 */
var TagCollection = Backbone.Collection.extend( LoggableMixin ).extend({   
    model : Tag,
    
    // uncomment this out see log messages
    logger              : console,

    toString : function(){
        return 'TagCollection()';
    }
});

//------------------------------------------------------------------------------
/** View for a TagCollection (and it's controls) - as per an hda's tag controls on the history panel
 */
var TagList = BaseView.extend( LoggableMixin ).extend({

    // uncomment this out see log messages
    logger              : console,

    toString : function(){
        return 'TagList()';
    }
});