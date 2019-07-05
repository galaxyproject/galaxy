var Region = module.exports = function(){
	this._start1 = null;
    this._end1 = null;
    this._start2 = null;
    this._end2 = null;
}

Region.prototype.getStart1 = function(){
	return this._start1;
}

Region.prototype.setStart1 = function(start1){
	this._start1 = start1;
}

Region.prototype.getEnd1 = function(){
	return this._end1;
}

Region.prototype.setEnd1 = function(end1){
	this._end1 = end1;
}

Region.prototype.getStart2 = function(){
	return this._start2;
}

Region.prototype.setStart2 = function(start2){
	this._start2 = start2;
}

Region.prototype.getEnd2 = function(){
	return this._end2;
}

Region.prototype.setEnd2 = function(end2){
	this._end2 = end2;
}
