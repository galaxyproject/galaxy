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


class ToursRegistry(object):

    def __init__(self, tour_directories, app):
        # All tours provided by Galaxy mainline code
        self.tour_directories = util.config_directories_from_setting(tour_directories.split(','))
        self.load_tours()
        
        # Also add tours installed via toolsheds
        self.load_tours_from_shed_repositories(app)

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

    def unload_tour(self, tour_id):
        # This removes self.app.tour_registry.tours[tour_id]
        try:
            del(self.tours[tour_id])
        except:
            log.warning("Trying to unload missing Interactive Tour: %s" , tour_id )

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
        tour_id = os.path.abspath(tour_path)
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

    def load_tours_from_shed_repositories(self, app):
        query = app.install_model.context.query( app.install_model.ToolShedRepository ) \
                                           .order_by( app.install_model.ToolShedRepository.table.c.name )
        for tool_shed_repository in query.all():
            if 'interactive_tours' in tool_shed_repository.metadata:
                for interactive_tour in  tool_shed_repository.metadata['interactive_tours']:
                    interactive_tour_path = str(interactive_tour[0])
                    if os.path.isfile(interactive_tour_path):
                        self._load_tour_from_path(interactive_tour_path)
