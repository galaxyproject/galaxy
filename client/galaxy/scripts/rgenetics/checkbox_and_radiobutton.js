/*
Scripts to create interactive checkboxes and radio buttons in SVG using ECMA script
Copyright (C) <2007>  <Andreas Neumann>
Version 1.1.3, 2007-08-09
neumann@karto.baug.ethz.ch
http://www.carto.net/
http://www.carto.net/neumann/

Credits:
* Guy Morton for providing a fix to let users toggle checkboxes by clicking on text labels
* Bruce Rindahl for providing the bugfix described in version 1.1.2
* Simon Shutter for providing a fix for the ASV in IE crash when reloading the SVG file after calling the .remove() method on a checkbox

----

Documentation: http://www.carto.net/papers/svg/gui/checkbox_and_radiobutton/

----

current version: 1.1.3

version history:
1.0 (2006-03-13)
initial version

1.1 (2006-07-11)
text labels are now clickable (thanks to Guy Morton)
added method .moveTo() to move checkbox to a different location
introduced new constructor parameter labelYOffset to allow more flexible placement of the text label

1.1.1 (2007-02-06)
added cursor pointer to the text label and use element representing the checkBox

1.1.2 (2007-04-19)
bug fix: this.selectedIndex was not correctly initialized in method addCheckBox of the radioButtonGroup object

1.1.3 (2007-08-09)
bug fix: the method .remove() was slightly modified (using removeEventListener) for avoiding a crash related to the method after reloading the SVG file

-------


This ECMA script library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library (lesser_gpl.txt); if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

----

original document site: http://www.carto.net/papers/svg/gui/checkbox_and_radiobutton/
Please contact the author in case you want to use code or ideas commercially.
If you use this code, please include this copyright header, the included full
LGPL 2.1 text and read the terms provided in the LGPL 2.1 license
(http://www.gnu.org/copyleft/lesser.txt)

-------------------------------

Please report bugs and send improvements to neumann@karto.baug.ethz.ch
If you use this control, please link to the original (http://www.carto.net/papers/svg/gui/checkbox_and_radiobutton/)
somewhere in the source-code-comment or the "about" of your project and give credits, thanks!

*/

function checkBox(id,parentNode,x,y,checkboxId,checkcrossId,checkedStatus,labelText,textStyles,labelDistance,labelYOffset,radioButtonGroup,functionToCall) {
	var nrArguments = 13;
	var createCheckbox= true;
	if (arguments.length == nrArguments) {	
		this.id = id; //an internal id, this id is not used in the SVG Dom tree
		this.parentNode = parentNode; //the parentNode, string or nodeReference
		this.x = x; //the center of the checkBox
		this.y = y; //the center of the checkBox
		this.checkboxId = checkboxId; //the id of the checkbox symbol (background)
		this.checkcrossId = checkcrossId; //the id of the checkbox symbol (foreground), pointer-events should be set to "none"
		this.checkedStatus = checkedStatus; //a status variable (true|false), indicates if checkbox is on or off
		this.labelText = labelText; //the text of the checkbox label to be displayed, use undefined or empty string if you don't need a label text
		this.textStyles = textStyles; //an array of literals containing the text settings
		if (!this.textStyles["font-size"]) {
			this.textStyles["font-size"] = 12;
		}
		this.labelDistance = labelDistance; //a distance defined from the center of the checkbox to the left of the text of the label
		this.labelYOffset = labelYOffset; //a y offset value for the text label in relation to the checkbox symbol center
		this.radioButtonGroup = radioButtonGroup; //a reference to a radio button group, if this is a standalone checkBox, just use the parameter undefined
		this.functionToCall = functionToCall; //the function to call after triggering checkBox
		this.exists = true; //status that indicates if checkbox exists or not, is set to false after method .remove() was called
		this.label = undefined; //later a reference to the label text node
	}
	else {
		createCheckbox = false;
		alert("Error in checkbox ("+id+"): wrong nr of arguments! You have to pass over "+nrArguments+" parameters.");
	}
	if (createCheckbox) {
		//timer stuff
		this.timer = new Timer(this); //a Timer instance for calling the functionToCall
		if (this.radioButtonGroup) {
			this.timerMs = 0;
		}
		else {
			this.timerMs = 200; //a constant of this object that is used in conjunction with the timer - functionToCall is called after 200 ms
		}
		//create checkbox
		this.createCheckBox();
	}
	else {
		alert("Could not create checkbox with id '"+id+"' due to errors in the constructor parameters");		
	}
}

//this method creates all necessary checkbox geometry
checkBox.prototype.createCheckBox = function() {
	if (typeof(this.parentNode) == "string") {
		this.parentNode = document.getElementById(this.parentNode);
	}
	//create checkbox
	this.checkBox = document.createElementNS(svgNS,"use");
	this.checkBox.setAttributeNS(null,"x",this.x);
	this.checkBox.setAttributeNS(null,"y",this.y);
	this.checkBox.setAttributeNS(xlinkNS,"href","#"+this.checkboxId);
	this.checkBox.addEventListener("click",this,false);
	this.checkBox.setAttributeNS(null,"cursor","pointer");
	this.parentNode.appendChild(this.checkBox);
	//create checkcross
	this.checkCross = document.createElementNS(svgNS,"use");
	this.checkCross.setAttributeNS(null,"x",this.x);
	this.checkCross.setAttributeNS(null,"y",this.y);
	this.checkCross.setAttributeNS(xlinkNS,"href","#"+this.checkcrossId);
	this.parentNode.appendChild(this.checkCross);
	if (this.checkedStatus == false) {
		this.checkCross.setAttributeNS(null,"display","none");
	}
	//create label, if any
	if (this.labelText) {
		if (this.labelText.length > 0) {
			this.label = document.createElementNS(svgNS,"text");
			for (var attrib in this.textStyles) {
				var value = this.textStyles[attrib];
				if (attrib == "font-size") {
					value += "px";
				}
				this.label.setAttributeNS(null,attrib,value);
			}
			this.label.setAttributeNS(null,"x",(this.x + this.labelDistance));
			this.label.setAttributeNS(null,"y",(this.y + this.labelYOffset));
			this.label.setAttributeNS(null,"cursor","pointer");
			var labelTextNode = document.createTextNode(this.labelText);
			this.label.appendChild(labelTextNode);
			this.label.setAttributeNS(null,"pointer-events","all");
			this.label.addEventListener("click",this,false);
			this.parentNode.appendChild(this.label);
		}
	}
	if (this.radioButtonGroup) {
		this.radioButtonGroup.addCheckBox(this);
	}
}

checkBox.prototype.handleEvent = function(evt) {
	if (evt.type == "click") {
		if (this.checkedStatus == true) {
			this.checkCross.setAttributeNS(null,"display","none");
			this.checkedStatus = false;
		}
		else {
			this.checkCross.setAttributeNS(null,"display","inline");
			this.checkedStatus = true;
		}
	}
	this.timer.setTimeout("fireFunction",this.timerMs);
}

checkBox.prototype.fireFunction = function() {
	if (this.radioButtonGroup) {
		this.radioButtonGroup.selectById(this.id,true);
	}
	else {
		if (typeof(this.functionToCall) == "function") {
			this.functionToCall(this.id,this.checkedStatus,this.labelText);
		}
		if (typeof(this.functionToCall) == "object") {
			this.functionToCall.checkBoxChanged(this.id,this.checkedStatus,this.labelText);
		}
		if (typeof(this.functionToCall) == undefined) {
			return;
		}
	}
}

checkBox.prototype.check = function(FireFunction) {
	this.checkCross.setAttributeNS(null,"display","inherit");
	this.checkedStatus = true;
	if (FireFunction) {
		this.timer.setTimeout("fireFunction",this.timerMs);
	}
}

checkBox.prototype.uncheck = function(FireFunction) {
	this.checkCross.setAttributeNS(null,"display","none");
	this.checkedStatus = false;
	if (FireFunction) {
		this.timer.setTimeout("fireFunction",this.timerMs);
	}
}

//move checkbox to a different position
checkBox.prototype.moveTo = function(moveX,moveY) {
    this.x = moveX;
    this.y = moveY;
    //move checkbox
 	this.checkBox.setAttributeNS(null,"x",this.x);
	this.checkBox.setAttributeNS(null,"y",this.y);
    //move checkcross
	this.checkCross.setAttributeNS(null,"x",this.x);
	this.checkCross.setAttributeNS(null,"y",this.y);
    //move text label
	if (this.labelText) {
		this.label.setAttributeNS(null,"x",(this.x + this.labelDistance));
		this.label.setAttributeNS(null,"y",(this.y + this.labelYOffset));
    }
}

checkBox.prototype.remove = function(FireFunction) {
	this.checkBox.removeEventListener("click",this,false);
	this.parentNode.removeChild(this.checkBox);
	this.parentNode.removeChild(this.checkCross);
	if (this.label) {
		this.parentNode.removeChild(this.label);	
	}
	this.exists = false;
}

checkBox.prototype.setLabelText = function(labelText) {
	this.labelText = labelText
	if (this.label) {
		this.label.firstChild.nodeValue = labelText;
	}
	else {
		if (this.labelText.length > 0) {
			this.label = document.createElementNS(svgNS,"text");
			for (var attrib in this.textStyles) {
				value = this.textStyles[attrib];
				if (attrib == "font-size") {
					value += "px";
				}
				this.label.setAttributeNS(null,attrib,value);
			}
			this.label.setAttributeNS(null,"x",(this.x + this.labelDistance));
			this.label.setAttributeNS(null,"y",(this.y + this.textStyles["font-size"] * 0.3));
			var labelTextNode = document.createTextNode(this.labelText);
			this.label.appendChild(labelTextNode);
			this.parentNode.appendChild(this.label);
		}	
	}
}

/* start of the radioButtonGroup object */

function radioButtonGroup(id,functionToCall) {
	var nrArguments = 2;
	if (arguments.length == nrArguments) {	
		this.id = id;
		if (typeof(functionToCall) == "function" || typeof(functionToCall) == "object" || typeof(functionToCall) == undefined) {
			this.functionToCall = functionToCall;
		}
		else {
			alert("Error in radiobutton with ("+id+"): argument functionToCall is not of type 'function', 'object' or undefined!");		
		}
		this.checkBoxes = new Array(); //this array will hold checkbox objects
		this.selectedId = undefined; //holds the id of the active radio button
		this.selectedIndex = undefined; //holds the index of the active radio button
		//timer stuff
		this.timer = new Timer(this); //a Timer instance for calling the functionToCall
		this.timerMs = 200; //a constant of this object that is used in conjunction with the timer - functionToCall is called after 200 ms
	}
	else {
		alert("Error in radiobutton with ("+id+"): wrong nr of arguments! You have to pass over "+nrArguments+" parameters.");
	}
}

radioButtonGroup.prototype.addCheckBox = function(checkBoxObj) {
	this.checkBoxes.push(checkBoxObj);
	if (checkBoxObj.checkedStatus) {
		this.selectedId = checkBoxObj.id;
		this.selectedIndex = this.checkBoxes.length - 1;
	}
}

//change radio button selection by id
radioButtonGroup.prototype.selectById = function(cbId,fireFunction) {
	var found = false;
	for (var i=0;i<this.checkBoxes.length;i++) {
		if (this.checkBoxes[i].id == cbId) {
			this.selectedId = cbId;
			this.selectedIndex = i;
			if (this.checkBoxes[i].checkedStatus == false) {
				this.checkBoxes[i].check(false);
			}
			found = true;
		}
		else {
			this.checkBoxes[i].uncheck(false);
		}
	}
	if (found) {
		if (fireFunction) {
			this.timer.setTimeout("fireFunction",this.timerMs);
		}
	}
	else {
		alert("Error in radiobutton with ("+this.id+"): could not find checkbox with id '"+cbId+"'");	
	}
}

//change radio button selection by label name
radioButtonGroup.prototype.selectByLabelname = function(labelName,fireFunction) {
	var id = -1;
	for (var i=0;i<this.checkBoxes.length;i++) {
		if (this.checkBoxes[i].labelText == labelName) {
			id = this.checkBoxes[i].id;
		}
	}
	if (id == -1) {
		alert("Error in radiobutton with ("+this.id+"): could not find checkbox with label '"+labelName+"'");
	}
	else {
		this.selectById(id,fireFunction);	
	}
}

radioButtonGroup.prototype.fireFunction = function() {
	if (typeof(this.functionToCall) == "function") {
		this.functionToCall(this.id,this.selectedId,this.checkBoxes[this.selectedIndex].labelText);
	}
	if (typeof(this.functionToCall) == "object") {
		this.functionToCall.radioButtonChanged(this.id,this.selectedId,this.checkBoxes[this.selectedIndex].labelText);
	}
	if (typeof(this.functionToCall) == undefined) {
		return;
	}
}