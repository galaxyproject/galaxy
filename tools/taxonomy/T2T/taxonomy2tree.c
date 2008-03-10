
#include "avl.h"
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <math.h>
#include <time.h>
#include <ctype.h>

#define	DEFAULT_STRING_ALLOC	  16L
#define	NUMBER_OF_FIELDS		  24
#define NUMBER_OF_TAX_FIELDS	  22
#define AVL_THRESHOLD			  64

char    *rankLabels [NUMBER_OF_TAX_FIELDS] = 
	 	{"root"        ,
        "superkingdom",
        "kingdom"     ,
        "subkingdom"  ,
        "superphylum" ,
        "phylum"      ,
        "subphylum"   ,
        "superclass"  ,
        "class"       ,
        "subclass"    ,
        "superorder"  ,
        "order"       ,
        "suborder"    ,
        "superfamily" ,
        "family"      ,
        "subfamily"   ,
        "tribe"       ,
        "subtribe"    ,
        "genus"       ,
        "subgenus"    ,
        "species"     ,
        "subspecies"  
};

static char *const Usage = "taxonomy2tree tax_dump_file(tab separated taxonomy dump) max_tree_level (<=0 to show all levels) file_for_the_tree file_for_tab_sep_summary include-empty-nodes(optional; 0 or 1; default 0)\n";

/*---------------------------------------------------------------------------------------------------- */

void			check_pointer	(void*);

char			validTaxonNameChar[256];

long			currentLineID			= 1;

/*---------------------------------------------------------------------------------------------------- */

struct  avl_table *	  idTagAVL     = NULL,
				  *   uniqueTags   = NULL,
				  **  byLevel	   = NULL;

/*---------------------------------------------------------------------------------------------------- */

struct		bufferedString
{
	char *sData;
	long sLength,
		 saLength;
}
*globalNameBuffer;

/*---------------------------------------------------------------------------------------------------- */

struct		vector
{
	long *vData;

	long vLength,
		 vaLength;
};



/*---------------------------------------------------------------------------------------------------- */

void reportError (char * theMessage)
{
	fprintf (stderr, "\nERROR: %s\n", theMessage);
	exit (1);
}

/*---------------------------------------------------------------------------------------------------- */

void reportErrorLine (char * theMessage, long lineID)
{
	fprintf (stderr, "SKIPPED line %d: %s\n", lineID, theMessage);
}


/*---------------------------------------------------------------------------------------------------- */

struct bufferedString *allocateNewString (void)
{
	struct bufferedString *newS = (struct bufferedString*)malloc (sizeof (struct bufferedString));
	check_pointer (newS);
	check_pointer (newS->sData = (char*)malloc (DEFAULT_STRING_ALLOC+1));
	newS->sLength  = 0;
	newS->saLength = DEFAULT_STRING_ALLOC;
	newS->sData[0] = 0;
	return newS;
}

/*---------------------------------------------------------------------------------------------------- */

struct vector *allocateNewVector (void)
{
	struct vector *newS = (struct vector*)malloc (sizeof (struct vector));
	check_pointer (newS);
	check_pointer (newS->vData = (long*)malloc (DEFAULT_STRING_ALLOC*sizeof(long)));
	newS->vLength  = 0;
	newS->vaLength = DEFAULT_STRING_ALLOC;
	return newS;
}

/*---------------------------------------------------------------------------------------------------- */

void clear_buffered_string (struct bufferedString* theString)
{
	theString->sLength = 0;
}

/*---------------------------------------------------------------------------------------------------- */

void clear_vector (struct vector* v)
{
	v->vLength = 0;
}

/*---------------------------------------------------------------------------------------------------- */

void appendCharacterToString (struct bufferedString * s, const char c)
{
	long addThis; 
	if (s->saLength == s->sLength)
	{
		addThis = s->saLength / 8;
		if (DEFAULT_STRING_ALLOC > addThis)
			addThis = DEFAULT_STRING_ALLOC;
		s->saLength += addThis;
		check_pointer (s->sData = realloc (s->sData,s->saLength+1));
	}
	s->sData[s->sLength] = c;
	s->sData[++s->sLength] = 0;
}

/*---------------------------------------------------------------------------------------------------- */

void appendValueToVector (struct vector * v, long c)
{
	long addThis; 
	if (v->vaLength == v->vLength)
	{
		addThis = v->vaLength / 8;
		if (DEFAULT_STRING_ALLOC > addThis)
			addThis = DEFAULT_STRING_ALLOC;
		v->vaLength += addThis;
		check_pointer (v->vData = realloc (v->vData,sizeof(long)*v->vaLength));
	}
	v->vData[v->vLength++] = c;
}

/*---------------------------------------------------------------------------------------------------- */

long appendRangeToString (struct bufferedString * d, struct bufferedString *s, long from, long to)
{
	long addThis,
		 pl = to-from+1;
	
	if (pl<=0)
		return -1;
		
	if (d->saLength < d->sLength + pl)
	{
		addThis = d->saLength / 8;
		
		if (DEFAULT_STRING_ALLOC > addThis)
			addThis = DEFAULT_STRING_ALLOC;
		if (addThis < pl)
			addThis = pl;
			
		d->saLength += addThis;
		check_pointer (d->sData = realloc (d->sData,d->saLength+1));
	}
	for (addThis = from; addThis <=to; addThis++)
		d->sData[d->sLength++] = s->sData[addThis];

	d->sData[d->sLength] = 0;
	
	return pl;
}

/*---------------------------------------------------------------------------------------------------- */

void appendCharRangeToString (struct bufferedString * d, char * buffer)
{
	long addThis,
		 pl = strlen(buffer);
	
	if (pl<=0)
		return;
		
	if (d->saLength < d->sLength + pl)
	{
		addThis = d->saLength / 8;
		
		if (DEFAULT_STRING_ALLOC > addThis)
			addThis = DEFAULT_STRING_ALLOC;
		if (addThis < pl)
			addThis = pl;
			
		d->saLength += addThis;
		check_pointer (d->sData = realloc (d->sData,d->saLength+1));
	}
	for (addThis = 0; addThis <pl; addThis++)
		d->sData[d->sLength++] = buffer[addThis];

	d->sData[d->sLength] = 0;
	
}

/*---------------------------------------------------------------------------------------------------- */

long appendCharBufferToString (struct bufferedString * d, const char * b)
{
	long addThis,
		 pl = strlen (b);
	
	if (pl<=0)
		return -1;
		
	if (d->saLength < d->sLength + pl)
	{
		addThis = d->saLength / 8;
		
		if (DEFAULT_STRING_ALLOC > addThis)
			addThis = DEFAULT_STRING_ALLOC;
		if (addThis < pl)
			addThis = pl;
			
		d->saLength += addThis;
		check_pointer (d->sData = realloc (d->sData,d->saLength+1));
	}
	for (addThis = 0; addThis <pl; addThis++)
		d->sData[d->sLength++] = b[addThis];

	d->sData[d->sLength] = 0;
	return pl;
}

/*---------------------------------------------------------------------------------------------------- */
/*---------------------------------------------------------------------------------------------------- */

struct treeNode 
{
	struct treeNode * parent;
	long   startIndex,
		   hitCount,
		   length
		   ,beenhere;
		   
	struct vector   * children;
	struct avl_table* cachedChildren;
	
} *globalTreeRoot;

/*---------------------------------------------------------------------------------------------------- */

struct treeNode * allocateNewTreeNode (void)
{
	struct treeNode *newN = (struct treeNode*)malloc (sizeof (struct treeNode));
	check_pointer (newN);
	newN->parent = NULL;
	newN->startIndex     = 0;
	newN->length	     = 0;
	newN->hitCount       = 0;
	newN->beenhere		 = 0;
	newN->cachedChildren = NULL;
	newN->children		 = allocateNewVector();
	check_pointer (newN->children);
	return newN;
}

/*---------------------------------------------------------------------------------------------------- */

int compare_tree_nodes (const void *avl_a, const void *avl_b, void * xtra)
{
	long  t1 = ((struct treeNode*)avl_a)->startIndex,
		  t2 = ((struct treeNode*)avl_b)->startIndex;
		  
	if (t1 < t2)
		return -1;
	if (t1 > t2)
		return 1;
    
    return 0;
}

/*---------------------------------------------------------------------------------------------------- */

void	destroyTreeNode (struct treeNode* n)
{
	if (n->cachedChildren)
		avl_destroy (n->cachedChildren, NULL);
	free (n->children);
	free (n);
}

/*---------------------------------------------------------------------------------------------------- */

void	printTreeNode (FILE* f, struct treeNode* n)
{
	long i = 0;
	fprintf (f, "Node name: ");
	if (n->startIndex>=0)
	{
		for (;i < n->length; i++)
			fputc (globalNameBuffer->sData[n->startIndex + i], f);
	}
	else
		fprintf (f, " empty node");
	fprintf (f, "\nHit count %d (backup %d)\n", n->hitCount, n->beenhere);
}

/*---------------------------------------------------------------------------------------------------- */

void	traverseCheck (struct treeNode* n, char first)
{
	long i = 0;

	if (!first && n->startIndex >= 0 && n->beenhere != n->hitCount)
	{
		printTreeNode (stderr, n);
		//reportError ("DEATH AND DECAY, BIZNATCH!\n");
	}
	
	for (i = 0; i<n->children->vLength; i++)
		traverseCheck (((struct treeNode**)n->children->vData)[i], first);	
	
	if (first)
	{
		if (n->children->vLength == 0)
			n->beenhere = n->hitCount;

		if (n->parent)
			n->parent->beenhere += n->beenhere;
	}
}


/*---------------------------------------------------------------------------------------------------- */

void	traverseTree (FILE *summaryFile, struct treeNode* n, long maxDepth, long currentDepth)
{
	long i = 0;
	char c;
		
	if (currentDepth <= maxDepth)
	{
		if (n->children->vLength && maxDepth > currentDepth)
		{
			if (n->startIndex < 0)
			{
				for (i=0; i>n->startIndex && currentDepth - i < maxDepth; i--)
					fputc ('(', summaryFile);
				if (i == n->startIndex)
					i = 0;
			}
			else
				fputc ('(',summaryFile);

			if (i==0)
				for (; i<n->children->vLength; i++)
				{
					traverseTree (summaryFile, ((struct treeNode**)n->children->vData)[i], maxDepth, currentDepth+1);
					if (i<n->children->vLength-1)
						fputc (',',summaryFile);
				}
			
			if (n->startIndex < 0)
				for (i=0; i>n->startIndex+1 && currentDepth - i < maxDepth; i--)
					fprintf (summaryFile,")n:%d", n->hitCount);
			fputc (')',summaryFile);
		}
		
		if (n->startIndex>= 0)
		{
			for (i=n->startIndex; i<n->startIndex+n->length;i++)
			{
				c = globalNameBuffer->sData[i];
				if (validTaxonNameChar [c])
					fputc (c,summaryFile);
				else
					fputc ('_',summaryFile);
			}
			fprintf (summaryFile,":%d", n->hitCount);
		}
		else
			fprintf (summaryFile, "n:%d", n->hitCount);	
	}
}

/*---------------------------------------------------------------------------------------------------- */
struct treeNode * addAChild (struct treeNode* p, struct treeNode * c, char killIfD)
{
	struct treeNode * c2			= NULL;
	long			  i				= 0;
	char			  addNode		= 0;
	
	if (p->cachedChildren)
	{
		if ((c2 = ((struct treeNode*)avl_find (p->cachedChildren, c))) == NULL)
			addNode = 1;
		/*else
		{
			if (c2->startIndex > globalNameBuffer->sLength || c2->startIndex < 0)
				printf ("Reject node add %x %d %d\n", c2, c2->startIndex, c->startIndex);
		}*/
	}
	else
	{
		for (; i<p->children->vLength; i++)
			if (((struct treeNode**)p->children->vData)[i]->startIndex == c->startIndex)
				break;
		addNode = (p->children->vLength == i);
	}
	
	if (addNode)
	{
		if (c->parent && c->parent != p)
		{
			c2 = allocateNewTreeNode();
			c2->startIndex = c->startIndex;
			c2->length	   = c->length; 
			c2->hitCount   = 1;
			//if (p->cachedChildren)
			//	fprintf (stdout, "%x %x\n", p, c->parent);
			c = c2;

		}
		c->parent  = p;
		appendValueToVector (p->children, (long)c);
		if (p->children->vLength > AVL_THRESHOLD)
			if (p->cachedChildren == NULL)
			{
				//fprintf (stdout, "Switch %d\n", currentLineID);
				// switch over the the avl representation of nodes
				p->cachedChildren = avl_create (compare_tree_nodes, NULL, NULL);
				for (i=0; i<p->children->vLength; i++)
					avl_probe(p->cachedChildren, ((struct node**)p->children->vData)[i]);
			}
			else
				avl_probe (p->cachedChildren, c);
	}
	else
	{
		if (killIfD)
			destroyTreeNode (c);
		if (c2)
			return c2;
		else
			c = ((struct treeNode**)p->children->vData)[i];
			
	}
	return c;
}


/*---------------------------------------------------------------------------------------------------- */
/*---------------------------------------------------------------------------------------------------- */

struct		storedIDTag
{
	long		taxID,
				hit_count;
	struct		treeNode * tNode;
};

/*---------------------------------------------------------------------------------------------------- */

struct storedIDTag *allocateIDTag (void)
{
	struct storedIDTag *newS = (struct storedIDTag*)malloc (sizeof (struct storedIDTag));
	check_pointer (newS);
	newS->taxID		  = -1;
	newS->hit_count   = 0;
	newS->tNode		  = NULL;
	return newS;
}

/*---------------------------------------------------------------------------------------------------- */

int compare_id_tags (const void *avl_a, const void *avl_b, void * xtra)
{
	long  t1 = ((struct storedIDTag*)avl_a)->taxID,
		  t2 = ((struct storedIDTag*)avl_b)->taxID;
		  
	if (t1 < t2)
		return -1;
	if (t1 > t2)
		return 1;
    
    return 0;
}


/*---------------------------------------------------------------------------------------------------- */
/*---------------------------------------------------------------------------------------------------- */

struct		storedSequenceTag
{
	long		startIndex,
				length;
				
	struct		treeNode * refNode;
};

/*---------------------------------------------------------------------------------------------------- */

struct storedSequenceTag *allocateStringTag (void)
{
	struct storedSequenceTag *newS = (struct storedSequenceTag*)malloc (sizeof (struct storedSequenceTag));
	check_pointer (newS);
	newS->startIndex  = -1;
	newS->length	  = 0;
	newS->refNode	  = NULL;
	return newS;
}


/*---------------------------------------------------------------------------------------------------- */
/*
struct storedSequenceTag * storedSequenceTag (void)
{
	struct storedSequenceTag *newS = (struct storedSequenceTag*)malloc (sizeof (struct storedSequenceTag));
	check_pointer		(newS);
	newS->startIndex	= 0;
	newS->length		= 0;
	return newS;
}*/

/*---------------------------------------------------------------------------------------------------- */

int compare_tags (const void *avl_a, const void *avl_b, void * xtra)
{
    char* n1 = globalNameBuffer->sData+((struct storedSequenceTag*)avl_a)->startIndex,
		* n2 = globalNameBuffer->sData+((struct storedSequenceTag*)avl_b)->startIndex;
		
	long  l1 = ((struct storedSequenceTag*)avl_a)->length,
		  l2 = ((struct storedSequenceTag*)avl_b)->length,
		  i;
		  
	signed char c;
		  
	for (i = 0; i < l1 && i < l2; i++)
	{
		c = n1[i] - n2[i];
		if (c < 0)
			return -1;
		if (c>0)
			return 1;
	}
	
	if (l1 < l2)
		return -1;
	if (l1 > l2)
		return 1;
    
    return 0;
}

/*---------------------------------------------------------------------------------------------------- */
/*---------------------------------------------------------------------------------------------------- */

void	check_pointer (void * p)
{
    if (p == NULL)
    {
        fprintf (stderr,"Memory allocation error\n");
        exit (1);
    }
}

/*---------------------------------------------------------------------------------------------------- */

int		compare_strings (const struct bufferedString * s1, const struct bufferedString * s2)
{
	long upTo,
		 i;
		 
	if  (s1->sLength>s2->sLength)
		upTo = s2->sLength;
	else
		upTo = s1->sLength;

	for (i=0; i<upTo; i++)
	{
		int res = (s1->sData[i]-s2->sData[i]);
	 	if (res < 0)
	 		return -1;
	 	else
	 		if (res>0)
	 			return 1;
	}
	
	if (s1->sLength == s2->sLength)
		return 0;

	return 1-2*(s1->sLength<s2->sLength);
}

/*---------------------------------------------------------------------------------------------------- */

void destroy_string (struct bufferedString* aStr)
{
	free (aStr->sData);
	free (aStr);
}


/*---------------------------------------------------------------------------------------------------- */

int main (int argc, const char * argv[]) 
{
		
	struct	bufferedString			**currentBuffers;
									
	struct  storedIDTag				*aTag = allocateIDTag(),
									*aTag2;
									
	struct  storedSequenceTag		*sTag = allocateStringTag(),
									*sTag2,
									*sTag3;
									
	struct  avl_traverser			avlt;
									
	struct  treeNode				*currentParent = NULL,
									*currentNode;
																		
	char	automatonState			= 0,
			currentField			= 0,
			currentChar				= 0,
			showEmptyNodes			= 0;
						
	long	expectedFields			= NUMBER_OF_FIELDS,
			indexer,
			indexer2,
			indexer3,
			maxTreeLevel			= 0,
			setEOF					= 0,
			nRunCounter				= 0;
			
	FILE  	* treeFile				= NULL,
			* summaryFile			= NULL,
			* inFile				= NULL;
									
	globalNameBuffer  = allocateNewString();			
	globalTreeRoot	  = allocateNewTreeNode();
	currentBuffers    = (struct	bufferedString**)malloc (expectedFields*sizeof (struct	bufferedString*));
	byLevel			  = (struct avl_table**)malloc (sizeof (struct avl_table*) * NUMBER_OF_TAX_FIELDS);
	check_pointer	  (uniqueTags		  = avl_create (compare_tags, NULL, NULL));
	check_pointer	  (idTagAVL		      = avl_create (compare_id_tags, NULL, NULL));
	
	for (indexer = 0; indexer < NUMBER_OF_TAX_FIELDS; indexer++)
		check_pointer (byLevel[indexer] = avl_create (compare_tags, NULL, NULL));
		
	for (indexer = 0; indexer < expectedFields; indexer++)
		currentBuffers[indexer] = allocateNewString();
			
    if (argc != 6 && argc != 5)
    {
		fprintf (stderr,"%s",Usage);
        return 1;
    }
	
	maxTreeLevel = atoi (argv[2]);
		
    inFile		   = fopen (argv[1], "rb"); 
	if (!inFile)
	{
		fprintf (stderr, "Failed to open the input file %s\n", argv[1]);
		return 1;
	}

	treeFile		   = fopen (argv[3], "wb"); 
	if (!treeFile)
	{
		fprintf (stderr, "Failed to open the tree output file %s\n", argv[3]);
		return 1;
	}

	summaryFile		   = fopen (argv[4], "wb"); 
	if (!summaryFile)
	{
		fprintf (stderr, "Failed to open the summary output file %s\n", argv[4]);
		return 1;
	}
	
	if (argc == 6)
		showEmptyNodes = atoi (argv[5]);
	
	currentChar  = fgetc(inFile);
	currentField = 0;
	while (setEOF < 2)
	{
		switch (automatonState)
		{
			case 0: /* start of the line; expecting numbers or charcters */
				if (isalnum(currentChar))
				{
					automatonState = 1; /* reading sequence ID */
					appendCharacterToString(currentBuffers[currentField],toupper(currentChar));
				}
				else
					if (!(currentChar == '\n' || currentChar == '\r'))
					{
						reportErrorLine ("Could not find a valid gid number to start the line",currentLineID);
						automatonState = 6;
						continue;
					}
				break;
				
			case 1: /* reading sequence ID */
				if (currentChar == '\t')
				{
					automatonState = 2;
					continue;
				}
				else
				{
					if (currentChar == '\n' || currentChar == '\r')
					{
						reportErrorLine ("Expected a tab following the gid",currentLineID);
						automatonState = 6;
						continue;
					}
					else
						appendCharacterToString(currentBuffers[currentField],toupper(currentChar));
						
				}
				break;
					
			case 2: /* looking for a \t or a \n|\r*/
				if (currentChar == '\t')
				{
					currentField   ++;
					if (currentField < expectedFields)
						automatonState = 3;

						//reportErrorLine ("Too many fields",currentLineID);
						//automatonState = 6;
						//continue;
				}
				else
					if (currentChar == '\n' || currentChar == '\r')
					// finish the read
					{
						if (currentField < expectedFields-1) 
							reportErrorLine ("Too few fields",currentLineID);
						aTag->taxID     = atoi (currentBuffers[1]->sData);
						aTag->hit_count = 1;
						aTag2 = *(struct storedIDTag**)avl_probe(idTagAVL, aTag);
						//fprintf (stdout, "%d %d %x %x\n", currentLineID,aTag->taxID,aTag,aTag2);
						if (aTag == aTag2) // new taxID
						{
							// process fields
							currentParent = globalTreeRoot;
							nRunCounter   = 0;
							for (indexer = NUMBER_OF_FIELDS-NUMBER_OF_TAX_FIELDS; indexer < NUMBER_OF_FIELDS; indexer++)
							{
								indexer2 = strlen(currentBuffers[indexer]->sData);
								//fprintf (stdout, "%d %d\n", indexer, nRunCounter,indexer2);
								if ((currentBuffers[indexer])->sData[0] == 'n' && indexer2 == 1)
									nRunCounter++;
								else
								{
									indexer3 = globalNameBuffer->sLength;
									appendRangeToString (globalNameBuffer,currentBuffers[indexer],0,indexer2-1);									
									sTag->startIndex = indexer3;
									sTag->length	 = indexer2;
									sTag2			 = *(struct storedSequenceTag**)avl_probe (uniqueTags,sTag);
									if (sTag == sTag2) // added
										sTag = allocateStringTag();
									else
										globalNameBuffer->sLength = indexer3;
										
									sTag->startIndex = sTag2->startIndex;
									sTag->length	 = sTag2->length;
									
									sTag3 = *(struct storedSequenceTag**)avl_probe (byLevel[indexer-(NUMBER_OF_FIELDS-NUMBER_OF_TAX_FIELDS)],sTag);
									if (sTag == sTag3) // new node
									{
										//fprintf (stderr, "Add node level %d %d\n",indexer-(NUMBER_OF_FIELDS-NUMBER_OF_TAX_FIELDS), sTag2->startIndex);
										sTag3 = sTag;
										sTag3->refNode					= allocateNewTreeNode();
										sTag3->refNode->length			= sTag2->length;
										sTag3->refNode->startIndex		= sTag2->startIndex;
										sTag3->refNode->parent			= NULL;
										sTag = allocateStringTag();
									}
									//else
										//fprintf (stderr, "Have node %x %x %c%c %d\n",sTag3->refNode, (currentBuffers[indexer])->sData[0],(currentBuffers[indexer])->sData[1], currentParent->children->vLength);
									
									sTag3->refNode->hitCount++;
																			
									if (showEmptyNodes && nRunCounter>0)
									{
										currentNode             = allocateNewTreeNode();
										currentNode->startIndex = -nRunCounter;
										currentNode->hitCount	= 1;
										if (currentParent)
											currentParent = addAChild (currentParent,currentNode,1);
										else
											reportError ("Attempting to attach an empty node a null parent.");
									}
									
									if (currentParent)
										currentParent = addAChild (currentParent,sTag3->refNode,0);
									else
										currentParent = sTag3->refNode;
								
									nRunCounter = 0;
								}
							}
							if (nRunCounter>0)
							{
								currentNode             = allocateNewTreeNode();
								currentNode->startIndex = -nRunCounter;
								currentNode->hitCount	= 1;
								if (currentParent)
									currentParent = addAChild (currentParent,currentNode,1);
								else
									reportError ("Attempting to attach an empty node a null parent.");
							}
							aTag->tNode = currentParent;
							aTag = allocateIDTag();

						}
						else
						{
							aTag2->hit_count++;
							currentParent = aTag2->tNode;
							while (currentParent)
							{
								currentParent->hitCount++;
								currentParent = currentParent->parent;
							}
							//printf ("Duplicate tag %d %d\n", aTag2->hit_count, aTag2->taxID);
						}
						//traverseCheck (globalTreeRoot);
						automatonState = 5;
						continue;
					}
					else			
					{		
						if (currentField < expectedFields)
						{
							reportErrorLine ("Expected a tab following a field",currentLineID);
							automatonState = 6;
							continue;
						}
					}
				break;
				
			case 3: /* read a field */				
				if (currentChar == '\t')
				{
					automatonState = 2;
					continue;
				}
				else
					if (currentChar == '\n' || currentChar == '\r')
					{
						currentField++;
						automatonState = 2;
						continue;
					}
					else
					{
						if (currentChar == '\'')
							automatonState = 4;
						else
							appendCharacterToString(currentBuffers[currentField],currentChar);
					}
				break;
		
			case 4: /* inside ' ' */				
				if (currentChar == '\'')
					automatonState = 3;
				else
					if (currentChar == '\n' || currentChar == '\r')
					{
						reportErrorLine ("Premature line end while reading a literal",currentLineID);
						automatonState = 5;
					}
					else
						appendCharacterToString(currentBuffers[currentField],currentChar);
				break;
				
			case 5:
				automatonState = 0;
				currentLineID ++;
				currentField = 0;
				for (indexer = 0; indexer < expectedFields; indexer++)
					clear_buffered_string(currentBuffers[indexer]);
				break;
				
			case 6:
				if (currentChar == '\n' || currentChar == '\r')
					automatonState = 5;
				break;
		}
		currentChar = fgetc(inFile);
		if (feof (inFile))
		{
			setEOF		++;
			currentChar = '\n';
		}
	}
	
	fprintf (stderr, "Read %d unique taxIDs\n", avl_count (idTagAVL));
	
	fclose  (inFile);	
	
	indexer3 = ((maxTreeLevel>0)?(maxTreeLevel+1):0xfffffL);
	if (indexer3 > NUMBER_OF_TAX_FIELDS)
		indexer3 = NUMBER_OF_TAX_FIELDS; 
	for (indexer = 0; indexer < indexer3; indexer++)
	{
		avl_t_init (&avlt, byLevel[indexer]);
		sTag = (struct storedSequenceTag*)avl_t_first (&avlt, byLevel[indexer]);
		while (sTag)
		{
			fprintf (summaryFile, "%s\t", rankLabels[indexer]);
			for (indexer2 = 0; indexer2 < sTag->length; indexer2++)
				fputc(*(globalNameBuffer->sData+sTag->startIndex+indexer2),summaryFile);
			fprintf (summaryFile, "\t%d\n", sTag->refNode->hitCount);
			sTag = (struct storedSequenceTag*)avl_t_next (&avlt);
		}
		//fprintf (stderr, "Level %d unique IDs = %d\n", indexer, avl_count (byLevel[indexer]));
	}

	for (indexer = 0; indexer < 256; indexer ++)
		validTaxonNameChar[indexer] = 1;
		
	validTaxonNameChar[','] = 0;
	validTaxonNameChar[')'] = 0;
	validTaxonNameChar['('] = 0;
	validTaxonNameChar[':'] = 0;
	
	
	traverseTree (treeFile,((struct treeNode**)globalTreeRoot->children->vData)[0],(maxTreeLevel>0)?(maxTreeLevel+1):0xfffffL,0);
	fclose (treeFile);
	traverseCheck (((struct treeNode**)globalTreeRoot->children->vData)[0], 1);
	traverseCheck (((struct treeNode**)globalTreeRoot->children->vData)[0], 0);
	return 0;
}

