import os, sys

def print_out(data):
	build = str(data.dbkey)
	id = data.id
	extension = ["bed", "interval"]
	return (build,id,extension)

def print_name(data):
	if isinstance(data, list):
		name_list=[]
		for item in data:
			name_list.append("_NAME_" + item.name.replace("(","_OPEN_").replace(")","_CLOSE_").replace(" ","_SPACE_"))
		return name_list
	else:	
		return "_NAME_" + data.name.replace("(","_OPEN_").replace(")","_CLOSE_").replace(" ","_SPACE_")
	
