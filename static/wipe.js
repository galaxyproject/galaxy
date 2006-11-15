dojo.require("dojo.animation");

function wipeIn_dojo(node, duration, callback, dontPlay) 
{
   // Determine the full height of the element
   node.style.overflow = "visible";
   node.style.visibility = "hidden";
   // Prevents a flicker on mozilla
   if ( dojo.render.html.mozilla )
   {
       node.style.position = "absolute";
   }
   node.style.display = "block";
   var height = node.offsetHeight;
   // Restore
   node.style.display = "none";
   node.style.position = "";
   node.style.visibility = "";

   var anim = wipeInToHeight(node, duration, height, function(e) {
      node.style.height = "auto";
      node.style.display = "block";
      if(callback) { callback(node, anim); }
   }, dontPlay);
};

function wipeInToHeight(node, duration, height, callback, dontPlay) 
{
 	var savedOverflow = dojo.html.getStyle(node, "overflow");
 	node.style.display = "none";
 	node.style.height = 0;
 	if(savedOverflow == "visible") {
 		node.style.overflow = "hidden";
 	}
 	node.style.display = "block";

 	var anim = new dojo.animation.Animation(
 		new dojo.math.curves.Line([0], [height]),
 		duration, 0);
 	dojo.event.connect(anim, "onAnimate", function(e) {
 		node.style.height = Math.round(e.x) + "px";
 	});
 	dojo.event.connect(anim, "onEnd", function(e) {
 		if(savedOverflow != "visible") {
 			node.style.overflow = savedOverflow;
 		}
 		if(callback) { callback(node, anim); }
 	});
 	if( !dontPlay ) { anim.play(true); }
 	return anim;
 }

 function wipeOut_dojo(node, duration, callback, dontPlay) 
 {
 	var savedOverflow = dojo.html.getStyle(node, "overflow");
 	var savedHeight = dojo.html.getStyle(node, "height");
 	var height = node.offsetHeight;
 	node.style.overflow = "hidden";

 	var anim = new dojo.animation.Animation(
 		new dojo.math.curves.Line([height], [0]),
 		duration, 0);
 	dojo.event.connect(anim, "onAnimate", function(e) {
 		node.style.height = Math.round(e.x) + "px";
 	});
 	dojo.event.connect(anim, "onEnd", function(e) {
 		node.style.display = "none";
 		node.style.overflow = savedOverflow;
 		node.style.height = savedHeight || "auto";
 		if(callback) { callback(node, anim); }
 	});
 	if( !dontPlay ) { anim.play(true); }
 	return anim;
 };

 function wipeIn_simple( node, duration )
 {
     node.style.display = "block";
 }

 function wipeOut_simple( node, duration )
 {
     node.style.display = "none";
 }

 if ( dojo.render.html.safari || dojo.render.html.mozilla || dojo.render.html.ie60 )
 {
     wipeIn = wipeIn_dojo;
     wipeOut = wipeOut_dojo;
 }
 else
 {
     wipeIn = wipeIn_simple;
     wipeOut = wipeOut_simple;
 }