"""
This module manages loading/etc of Galaxy interactive tours.
"""

import os
import yaml
import logging
log = logging.getLogger( __name__ )


def tour_loader(contents_dict):
    #  This *COULD* be done on the clientside.  Maybe even should?
    title_default = contents_dict.get('title_default', None)
    for step in contents_dict['steps']:
        if 'intro' in step:
            step['content'] = step.pop('intro')
        if 'position' in step:
            step['placement'] = step.pop('position')
        if 'element' not in step:
            step['orphan'] = True
        if title_default:
            step['title'] = title_default
    return contents_dict


class ToursRegistry(object):

    def __init__(self, tour_dir):
        self.tour_dir = tour_dir
        self.load_tours()

    def tours_by_id_with_description(self):
        return [{'id': k,
                 'description': self.tours[k].get('description', None),
                 'name': self.tours[k].get('name', None)}
                for k in self.tours.keys()]

    def load_tours(self):
        self.tours = {}
        for filename in os.listdir(self.tour_dir):
            if filename.endswith('.yaml'):
                tour_path = os.path.join(self.tour_dir, filename)
                with open(tour_path) as handle:
                    try:
                        conf = yaml.load(handle)
                    except:
                        log.warning("Tour '%s' could not be loaded, please check if your yaml syntax is valid." % filename)
                        continue
                # Could pop the following, but is there a good reason to?
                # As long as they key doesn't conflict with tour keys, it's
                # fine.
                tour_id = filename.rstrip('.yaml')
                self.tours[tour_id] = tour_loader(conf)
                log.info("Loaded tour '%s'" % tour_id)

    def tour_contents(self, tour_id):
        # Extra format translation could happen here (like the previous intro_to_tour)
        # For now just return the loaded contents.
        return self.tours.get(tour_id, None)
