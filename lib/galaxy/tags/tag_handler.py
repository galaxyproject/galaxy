from galaxy.model import Tag, History, HistoryTagAssociation, Dataset, DatasetTagAssociation, HistoryDatasetAssociation, HistoryDatasetAssociationTagAssociation
import re

class TagHandler( object ):
    
    # Tag separator.
    tag_separators = ',;'
    
    # Hierarchy separator.
    hierarchy_separator = '.'
    
    # Key-value separator.
    key_value_separators = "=:"
    
    def __init__(self):
        self.tag_assoc_classes = dict()
        
    def add_tag_assoc_class(self, entity_class, tag_assoc_class):
        self.tag_assoc_classes[entity_class] = tag_assoc_class
        
    def get_tag_assoc_class(self, entity_class):
        return self.tag_assoc_classes[entity_class]
        
    # Remove a tag from an item.
    def remove_item_tag(self, item, tag_name):
        # Get item tag association.
        item_tag_assoc = self._get_item_tag_assoc(item, tag_name)
        
        # Remove association.
        if item_tag_assoc:
            # Delete association.
            item_tag_assoc.delete()
            item.tags.remove(item_tag_assoc)
            return True
        
        return False
    
    # Delete tags from an item.
    def delete_item_tags(self, item):
        # Delete item-tag associations.
        for tag in item.tags:
            tag.delete()
            
        # Delete tags from item.
        del item.tags[:]
        
    # Returns true if item is has a given tag.
    def item_has_tag(self, item, tag_name):
        # Check for an item-tag association to see if item has a given tag.
        item_tag_assoc = self._get_item_tag_assoc(item, tag_name)
        if item_tag_assoc:
            return True
        return False
            

    # Apply tags to an item.
    def apply_item_tags(self, db_session, item, tags_str):
        # Parse tags.
        parsed_tags = self._parse_tags(tags_str)
        
        # Apply each tag.
        for name, value in parsed_tags.items():
            # Get or create item-tag association.
            item_tag_assoc = self._get_item_tag_assoc(item, name)
            if not item_tag_assoc:
                #
                # Create item-tag association.
                #
                
                # Create tag; if None, skip the tag (and log error).
                tag = self._get_or_create_tag(db_session, name)
                if not tag:
                    # Log error?
                    continue
                
                # Create tag association based on item class.
                item_tag_assoc_class = self.tag_assoc_classes[item.__class__]
                item_tag_assoc = item_tag_assoc_class()
                
                # Add tag to association.
                item.tags.append(item_tag_assoc)
                item_tag_assoc.tag = tag
                    
            # Apply attributes to item-tag association. Strip whitespace from user name and tag.
            if value:
                trimmed_value = value.strip()
            else:
                trimmed_value = value
            item_tag_assoc.user_tname = name.strip()
            item_tag_assoc.user_value = trimmed_value
            item_tag_assoc.value = self._scrub_tag_value(value)
                
    # Build a string from an item's tags.
    def get_tags_str(self, tags):
        # Return empty string if there are no tags.
        if not tags:
            return ""
        
        # Create string of tags.
        tags_str_list = list()
        for tag in tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += ":" + tag.user_value
            tags_str_list.append(tag_str)
        return ", ".join(tags_str_list)            
    
    # Get a Tag object from a tag string.
    def _get_tag(self, db_session, tag_str):
        return db_session.query(Tag).filter(Tag.name==tag_str).first()
    
    # Create a Tag object from a tag string.
    def _create_tag(self, db_session, tag_str):
        tag_hierarchy = tag_str.split(self.__class__.hierarchy_separator)
        tag_prefix = ""
        parent_tag = None
        for sub_tag in tag_hierarchy:
            # Get or create subtag.
            tag_name = tag_prefix + self._scrub_tag_name(sub_tag)
            tag = db_session.query(Tag).filter(Tag.name==tag_name).first()
            if not tag:
                tag = Tag(type="generic", name=tag_name)
                
            # Set tag parent.
            tag.parent = parent_tag
            
            # Update parent and tag prefix.
            parent_tag = tag
            tag_prefix = tag.name + self.__class__.hierarchy_separator
        return tag
    
    # Get or create a Tag object from a tag string.
    def _get_or_create_tag(self, db_session, tag_str):
        # Scrub tag; if tag is None after being scrubbed, return None.
        scrubbed_tag_str = self._scrub_tag_name(tag_str)
        if not scrubbed_tag_str:
            return None
        
        # Get item tag.
        tag = self._get_tag(db_session, scrubbed_tag_str)
        
        # Create tag if necessary.
        if tag is None:
            tag = self._create_tag(db_session, scrubbed_tag_str)
            
        return tag
    
    # Return ItemTagAssociation object for an item and a tag string; returns None if there is
    # no such tag.
    def _get_item_tag_assoc(self, item, tag_name):
        scrubbed_tag_name = self._scrub_tag_name(tag_name)
        for item_tag_assoc in item.tags:
            if item_tag_assoc.tag.name == scrubbed_tag_name:
                return item_tag_assoc 
        return None
    
    # Returns a list of raw (tag-name, value) pairs derived from a string; method does not scrub tags. 
    # Return value is a dictionary where tag-names are keys.
    def _parse_tags(self, tag_str):
        # Gracefully handle None.
        if not tag_str:
            return dict()
        
        # Split tags based on separators.
        reg_exp = re.compile('[' + self.__class__.tag_separators + ']')
        raw_tags = reg_exp.split(tag_str)
        
        # Extract name-value pairs.
        name_value_pairs = dict()
        for raw_tag in raw_tags:
            nv_pair = self._get_name_value_pair(raw_tag)
            name_value_pairs[nv_pair[0]] = nv_pair[1]
        return name_value_pairs
    
    # Scrub a tag value.
    def _scrub_tag_value(self, value):
        # Gracefully handle None:
        if not value:
            return None
        
        # Remove whitespace from value.
        reg_exp = re.compile('\s')
        scrubbed_value = re.sub(reg_exp, "", value)
        
        # Lowercase and return.
        return scrubbed_value.lower()
    
    # Scrub a tag name.
    def _scrub_tag_name(self, name):
        # Gracefully handle None:
        if not name:
            return None
        
        # Remove whitespace from name.
        reg_exp = re.compile('\s')
        scrubbed_name = re.sub(reg_exp, "", name)
            
        # Ignore starting ':' char.
        if scrubbed_name.startswith(self.__class__.hierarchy_separator):
            scrubbed_name = scrubbed_name[1:]
            
        # If name is too short or too long, return None.
        if len(scrubbed_name) < 3 or len(scrubbed_name) > 255:
            return None
                
        # Lowercase and return.
        return scrubbed_name.lower()
    
    # Scrub a tag name list.
    def _scrub_tag_name_list(self, tag_name_list):
        scrubbed_tag_list = list()
        for tag in tag_name_list:
            scrubbed_tag_list.append(self._scrub_tag_name(tag))
        return scrubbed_tag_list
    
    # Get name, value pair from a tag string.
    def _get_name_value_pair(self, tag_str):
        # Use regular expression to parse name, value.
        reg_exp = re.compile("[" + self.__class__.key_value_separators + "]")
        name_value_pair = reg_exp.split(tag_str)
        
        # Add empty slot if tag does not have value.
        if len(name_value_pair) < 2:
            name_value_pair.append(None)
            
        return name_value_pair