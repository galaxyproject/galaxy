from Cheetah.Template import Template
import os

def fill_template( template_text, context=None, **kwargs ):
    if not context:
        context = kwargs
    #print "This is what context is: " + str(context)
#    context['pw'] = os.getenv('pw')
		
    #print str(context['pw']['__format__'])
    print "This is what fill template spits out: " + str( Template( source=template_text, searchList=[context]))
    return str( Template( source=template_text, searchList=[context] ) )
