/*==============================================================================
Backbone MV for Annotations


TODO:

==============================================================================*/
/** Single Tag model
 */
var Annotation = BaseModel.extend( LoggableMixin ).extend({
    
    // uncomment this out see log messages
    logger              : console,
     
    toString : function(){
        return 'Annotation()';
    }
});

//------------------------------------------------------------------------------
/** Single Tag view
 */
var AnnotationView = BaseView.extend( LoggableMixin ).extend({
    
    // uncomment this out see log messages
    logger              : console,

    toString : function(){
        return 'AnnotationView()';
    }
});

//==============================================================================
/** YAGNI? A collection of Annotations, mainView?
 */
