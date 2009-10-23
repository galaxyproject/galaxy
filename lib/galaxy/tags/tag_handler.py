from galaxy.model import Tag
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
        
    def remove_item_tag( self, trans, item, tag_name ):
        """Remove a tag from an item."""
        # Get item tag association.
        item_tag_assoc = self._get_item_tag_assoc(item, tag_name)
        
        # Remove association.
        if item_tag_assoc:
            # Delete association.
            trans.sa_session.delete( item_tag_assoc )
            item.tags.remove(item_tag_assoc)
            return True
        
        return False
    
    def delete_item_tags( self, trans, item ):
        """Delete tags from an item."""
        # Delete item-tag associations.
        for tag in item.tags:
            trans.sa_ession.delete( tag )
            
        # Delete tags from item.
        del item.tags[:]
        
    def item_has_tag(self, item, tag):
        """Returns true if item is has a given tag."""
        # Get tag name.
        if isinstance(tag, basestring):
            tag_name = tag
        elif isinstance(tag, Tag):
            tag_name = tag.name
        
        # Check for an item-tag association to see if item has a given tag.
        item_tag_assoc = self._get_item_tag_assoc(item, tag_name)
        if item_tag_assoc:
            return True
        return False
            

    def apply_item_tags(self, db_session, item, tags_str):
        """Apply tags to an item."""
        # Parse tags.
        parsed_tags = self.parse_tags(tags_str)
        
        # Apply each tag.
        for name, value in parsed_tags.items():
            # Use lowercase name for searching/creating tag.
            lc_name = name.lower()
            
            # Get or create item-tag association.
            item_tag_assoc = self._get_item_tag_assoc(item, lc_name)
            if not item_tag_assoc:
                #
                # Create item-tag association.
                #
                
                # Create tag; if None, skip the tag (and log error).
                tag = self._get_or_create_tag(db_session, lc_name)
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
            lc_value = None
            if value:
                lc_value = value.lower()
            item_tag_assoc.user_tname = name
            item_tag_assoc.user_value = value
            item_tag_assoc.value = lc_value
                
    def get_tags_str(self, tags):
        """Build a string from an item's tags."""
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
    
    def get_tag_by_id(self, db_session, tag_id):
        """Get a Tag object from a tag id."""
        return db_session.query(Tag).filter(Tag.id==tag_id).first()    
        
    def get_tag_by_name(self, db_session, tag_name):
        """Get a Tag object from a tag name (string)."""
        if tag_name:
            return db_session.query( Tag ).filter( Tag.name==tag_name.lower() ).first()
        return None
    
    def _create_tag(self, db_session, tag_str):
        """Create a Tag object from a tag string."""
        tag_hierarchy = tag_str.split(self.__class__.hierarchy_separator)
        tag_prefix = ""
        parent_tag = None
        for sub_tag in tag_hierarchy:
            # Get or create subtag.
            tag_name = tag_prefix + self._scrub_tag_name(sub_tag)
            tag = db_session.query(Tag).filter(Tag.name==tag_name).first()
            if not tag:
                tag = Tag(type=0, name=tag_name)
                
            # Set tag parent.
            tag.parent = parent_tag
            
            # Update parent and tag prefix.
            parent_tag = tag
            tag_prefix = tag.name + self.__class__.hierarchy_separator
        return tag
    
    def _get_or_create_tag(self, db_session, tag_str):
        """Get or create a Tag object from a tag string."""
        # Scrub tag; if tag is None after being scrubbed, return None.
        scrubbed_tag_str = self._scrub_tag_name(tag_str)
        if not scrubbed_tag_str:
            return None
        
        # Get item tag.
        tag = self.get_tag_by_name(db_session, scrubbed_tag_str)
        
        # Create tag if necessary.
        if tag is None:
            tag = self._create_tag(db_session, scrubbed_tag_str)
            
        return tag
    
    def _get_item_tag_assoc(self, item, tag_name):
        """Return ItemTagAssociation object for an item and a tag string; returns None if there is
            no such tag."""
        scrubbed_tag_name = self._scrub_tag_name(tag_name)
        for item_tag_assoc in item.tags:
            if item_tag_assoc.tag.name == scrubbed_tag_name:
                return item_tag_assoc 
        return None
    
    def parse_tags(self, tag_str):
        """Returns a list of raw (tag-name, value) pairs derived from a string; method scrubs tag names and values as well. 
           Return value is a dictionary where tag-names are keys."""
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
            scrubbed_name = self._scrub_tag_name( nv_pair[0] )
            scrubbed_value = self._scrub_tag_value( nv_pair[1] )
            name_value_pairs[scrubbed_name] = scrubbed_value
        return name_value_pairs
    
    def _scrub_tag_value(self, value):
        """Scrub a tag value."""
        # Gracefully handle None:
        if not value:
            return None
        
        # Remove whitespace from value.
        reg_exp = re.compile('\s')
        scrubbed_value = re.sub(reg_exp, "", value)
        
        return scrubbed_value
    
    def _scrub_tag_name(self, name):
        """Scrub a tag name."""
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
                
        return scrubbed_name
    
    def _scrub_tag_name_list(self, tag_name_list):
        """Scrub a tag name list."""
        scrubbed_tag_list = list()
        for tag in tag_name_list:
            scrubbed_tag_list.append( self._scrub_tag_name(tag) )
        return scrubbed_tag_list
    
    def _get_name_value_pair(self, tag_str):
        """Get name, value pair from a tag string."""
        # Use regular expression to parse name, value.
        reg_exp = re.compile( "[" + self.__class__.key_value_separators + "]" )
        name_value_pair = reg_exp.split( tag_str )
        
        # Add empty slot if tag does not have value.
        if len(name_value_pair) < 2:
            name_value_pair.append(None)
            
        return name_value_pair