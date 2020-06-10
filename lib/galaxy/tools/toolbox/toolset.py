
import os
import string
import yaml


class Toolset():

    def __init__(self, app):
        self._toolsets = {}
        self._toolset_name = ""
        self._tools_by_id = {}

    def toolset_list(self):
        self.toolsets.keys()

    def get_toolset(self, toolset_path):
        # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        # BASE_TOOLSET_DIR = os.path.join(BASE_DIR, "usegalaxy-eu-tools/")
        # toolset_path = os.path.join(BASE_TOOLSET_DIR, "bgruening.yaml")

        with open(toolset_path, 'r') as toolset_list:
            try:
                toolset = yaml.load(toolset_list)  # needs to be switched to safe_load but for some reason that's empty Juleen
                log.debug("Reading tools from %s finished", toolset_path)
                # log.debug(toolset['tools'])
                # print("\nTOOLSET DUMP: ", yaml.dump(toolset['tools']))  # to delete Juleen
                return toolset['tools']
            except yaml.YAMLError as exc:  # to fix later Juleen
                log.debug("Failed to read toolset list from %s", toolset_path)

    def get_all_toolsets(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        BASE_TOOLSET_DIR = os.path.join(BASE_DIR, "usegalaxy-eu-tools/")
        for filename in os.listdir(BASE_TOOLSET_DIR):
            if filename.endswith(".yaml"):
                toolset_path = os.path.join(BASE_TOOLSET_DIR, filename)
                self._toolset_name = filename[:-5]
                self._toolsets[self._toolset_name] = self.get_toolset(toolset_path)

                tool_ids = self.get_toolset_ids(self._toolset_name)
                print("TOOL_IDS: ", tool_ids)
            else:
                continue
        print("NUMBER TOOLSETS: ", len(self._toolsets))

    def get_toolset_ids(self, toolset_name):
        toolset = self._toolsets.get(toolset_name)
        return [tool['name'] for tool in toolset]
