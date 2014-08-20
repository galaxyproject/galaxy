import os,sys

#--------read tool_conf.xml to get all the tool xml file names-----------
onoff = 1
tool_list = []
for line in open("tool_conf.xml", "r"):
   if line.find("<!--") != -1:
      onoff = 0
   if line.find("file") != -1 and onoff==1:
      strs = line.split('\"')
      tool_list.append(strs[1])
   if line.find("<section") != -1 and onoff==1:
      keys = line.strip().split('\"')
      n = 0
      strtmp = "section::"
      while n < len(keys) :
         if keys[n].find("id") != -1 : strtmp = strtmp + keys[n+1]
         if keys[n].find("name") != -1 : strtmp = strtmp + keys[n+1] + "-"
         n = n + 1
      tool_list.append(strtmp.replace(' ', '_'))
   if line.find("-->") != -1:
      onoff =1

#-------read tool info from every tool xml file--------------------------
name = []
id = []
desc = []
tool_infos = []
for tool in tool_list :
   if tool.find("section")!=-1 :
      tool_info = dict()
      tool_info["id"] = tool
      tool_infos.append(tool_info)
   if os.path.exists("tools/"+tool) :
      for line in open("tools/"+tool) :
         if line.find("<tool ") != -1 and line.find("id") != -1 :
            keys = line.strip().split('\"')
            tool_info = dict()
            tool_info["desc"] = ''
            for n in range(len(keys)-1):
               if " id=" in keys[n]:
                  tool_info["id"] = keys[n+1].replace(' ', '_')
               if " name=" in keys[n]:
                  tool_info["name"] = keys[n+1]
               if " description=" in keys[n]:
                  tool_info["desc"] = keys[n+1]
            tool_infos.append(tool_info)
            break

flag=0
if len(sys.argv) == 1 :
   for tool_info in tool_infos:
      if tool_info["id"].find("section") != -1 :
         print "==========================================================================================================================================="
         print "%-45s\t%-40s\t%s" % ("id", "name", tool_info["id"])
         print "- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -"
      else :
         print "%-45s\t%-40s" % (tool_info["id"], tool_info["name"])
else:
   for tool_info in tool_infos:
      if tool_info["id"].find("section") != -1 :
         flag=0
      elif flag==1:
         print " functional.test_toolbox:TestForTool_%s" % tool_info["id"],
      if tool_info["id"].replace('section::', '')==sys.argv[1]:
         flag=1

#for key in tool_infos.keys():
#   print tool_infos[key]["id"], "\t", tool_infos[key]["name"], "\t", tool_infos[key]["desc"]
