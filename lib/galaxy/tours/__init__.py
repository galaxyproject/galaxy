"""
This module manages loading/etc of Galaxy interactive tours.
"""

import os
import yaml
import logging

from galaxy import util

log = logging.getLogger( __name__ )


def tour_loader(contents_dict):
    #  Some of this can be done on the clientside.  Maybe even should?
    title_default = contents_dict.get('title_default', None)
    for step in contents_dict['steps']:
        if 'intro' in step:
            step['content'] = step.pop('intro')
        if 'position' in step:
            step['placement'] = step.pop('position')
        if 'element' not in step:
            step['orphan'] = True
        if title_default and 'title' not in step:
            step['title'] = title_default
    return contents_dict

def _load_shed_tour_paths(shed_tool_path):
    # somehow figure out XML installation path
    # ../shed_tools/toolshed.g2.bx.psu.edu/tours/iuc/tourname/revision/tour_a.yaml
    paths = []
    for tool_shed in os.listdir(shed_tool_path):
        path1 = os.path.join(shed_tool_path, tool_shed, 'repos')
        if os.path.isdir(path1):
            for maintainer in os.listdir(path1):
                path2 = os.path.join(path1, maintainer)
                if os.path.isdir(path2):
                    for tour_name in os.listdir(path2):
                        path3 = os.path.join(path2, tour_name)
                        if os.path.isdir(path3):
                            for revision in os.listdir(path3):
                                path4 = os.path.join(path3, revision)
                                if os.path.isdir(path4):
                                    for repo in os.listdir(path4):
                                        path5 = os.path.join(path4, repo)
                                        if os.path.isdir(path5):
                                            paths.append(path5)
    fh = open('/tmp/a.txt','w')
    fh.write(str(paths))
    fh.close()
    return paths



class ToursRegistry(object):

    def __init__(self, tour_directories):
        # All tours provided by Galaxy mainline code
        all_tour_directories = tour_directories.split(',')
        # Also add tours installed via toolsheds
        all_tour_directories += _load_shed_tour_paths('../shed_tools')

        self.tour_directories = util.config_directories_from_setting(all_tour_directories)
        self.load_tours()

    def tours_by_id_with_description(self):
        return [{'id': k,
                 'description': self.tours[k].get('description', None),
                 'name': self.tours[k].get('name', None)}
                for k in self.tours.keys()]

    def load_tour(self, tour_id):
        for tour_dir in self.tour_directories:
            tour_path = os.path.join(tour_dir, tour_id + ".yaml")
            if not os.path.exists(tour_path):
                tour_path = os.path.join(tour_dir, tour_id + ".yml")
            if os.path.exists(tour_path):
                break
        if os.path.exists(tour_path):
            return self._load_tour_from_path(tour_path)
        else:
            return None

    def load_tours(self):
        self.tours = {}
        for tour_dir in self.tour_directories:
            for filename in os.listdir(tour_dir):
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    self._load_tour_from_path(os.path.join(tour_dir, filename))
        return self.tours_by_id_with_description()

    def tour_contents(self, tour_id):
        # Extra format translation could happen here (like the previous intro_to_tour)
        # For now just return the loaded contents.
        return self.tours.get(tour_id, None)

    def _load_tour_from_path(self, tour_path):
        filename = os.path.basename(tour_path)
        tour_id = os.path.splitext(filename)[0]
        try:
            with open(tour_path) as handle:
                conf = yaml.load(handle)
                tour = tour_loader(conf)
                self.tours[tour_id] = tour_loader(conf)
                log.info("Loaded tour '%s'" % tour_id)
                return tour
        except IOError:
            log.exception("Tour '%s' could not be loaded, error reading file." % tour_id)
        except yaml.error.YAMLError:
            log.exception("Tour '%s' could not be loaded, error within file.  Please check your yaml syntax." % tour_id)
        return None
