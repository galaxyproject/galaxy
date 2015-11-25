/*
tip_followscroll.js	v. 1.11

The latest version is available at
http://www.walterzorn.com
or http://www.devira.com
or http://www.walterzorn.de

Initial author: Walter Zorn
Last modified: 3.6.2008

Extension for the tooltip library wz_tooltip.js.
Lets a "sticky" tooltip keep its position inside the clientarea if the window
is scrolled.
*/

// Make sure that the core file wz_tooltip.js is included first
if(typeof config == "undefined")
	alert("Error:\nThe core tooltip script file 'wz_tooltip.js' must be included first, before the plugin files!");

// Here we define new global configuration variable(s) (as members of the
// predefined "config." class).
// From each of these config variables, wz_tooltip.js will automatically derive
// a command which can be passed to Tip() or TagToTip() in order to customize
// tooltips individually. These command names are just the config variable
// name(s) translated to uppercase,
// e.g. from config. FollowScroll a command FOLLOWSCROLL will automatically be
// created.

//===================	GLOBAL TOOLTIP CONFIGURATION	======================//
config. FollowScroll = false		// true or false - set to true if you want this to be the default behaviour
//=======	END OF TOOLTIP CONFIG, DO NOT CHANGE ANYTHING BELOW	==============//


// Create a new tt_Extension object (make sure that the name of that object,
// here fscrl, is unique amongst the extensions available for
// wz_tooltips.js):
var fscrl = new tt_Extension();

// Implement extension eventhandlers on which our extension should react
fscrl.OnShow = function()
{
	if(tt_aV[FOLLOWSCROLL])
	{
		// Permit FOLLOWSCROLL only if the tooltip is sticky
		if(tt_aV[STICKY])
		{
			var x = tt_x - tt_GetScrollX(), y = tt_y - tt_GetScrollY();

			if(tt_ie)
			{
				fscrl.MoveOnScrl.offX = x;
				fscrl.MoveOnScrl.offY = y;
				fscrl.AddRemEvtFncs(tt_AddEvtFnc);
			}
			else
			{
				tt_SetTipPos(x, y);
				tt_aElt[0].style.position = "fixed";
			}
			return true;
		}
		tt_aV[FOLLOWSCROLL] = false;
	}
	return false;
};
fscrl.OnHide = function()
{
	if(tt_aV[FOLLOWSCROLL])
	{
		if(tt_ie)
			fscrl.AddRemEvtFncs(tt_RemEvtFnc);
		else
			tt_aElt[0].style.position = "absolute";
	}
};
// Helper functions (encapsulate in the class to avoid conflicts with other
// extensions)
fscrl.MoveOnScrl = function()
{
	tt_SetTipPos(fscrl.MoveOnScrl.offX + tt_GetScrollX(), fscrl.MoveOnScrl.offY + tt_GetScrollY());
};
fscrl.AddRemEvtFncs = function(PAddRem)
{
	PAddRem(window, "resize", fscrl.MoveOnScrl);
	PAddRem(window, "scroll", fscrl.MoveOnScrl);
};

