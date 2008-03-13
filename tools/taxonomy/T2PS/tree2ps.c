
#include "avl.h"
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <math.h>
#include <time.h>
#include <ctype.h>

#define	DEFAULT_STRING_ALLOC	  16L
#define NUMBER_OF_TAX_FIELDS	  22

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

static char *const Usage = "tree2ps newick_file ps_output_file max_tree_level (<=0 to show all levels) font_size (in 2-255, 8 is a good default) \nmax_leaves (<=0 to show all) count_duplicate_tax_id (0 or 1; with 0 multiple copies of the same taxid count as 1)\n";
char		 validTaxonNameChar[256];

long		 fontSize		 = 8,
			 showMaxNodes    = 0;

double		 ySpacing,
			 xPadding,
			 globalXPad,
			 globalYPad,
			 lineWidth   = 2.,
			 countScaler;
			 
char		 countDuplicateTaxID = 0;

/*---------------------------------------------------------------------------------------------------- */

double  _timesCharWidths[256]= // Hardcoded relative widths of all 255 characters in the Times font, for the use of PSTreeString
	{
	0,0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0,0.25098,0.721569,0.721569,0.721569,0,0.721569,0.721569,
	0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0.721569,0,0.721569,0.721569,
	0.25098,0.333333,0.407843,0.501961,0.501961,0.831373,0.776471,0.180392,0.333333,0.333333,0.501961,0.564706,0.25098,0.333333,0.25098,0.278431,
	0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,0.278431,0.278431,0.564706,0.564706,0.564706,0.443137,
	0.921569,0.721569,0.666667,0.666667,0.721569,0.611765,0.556863,0.721569,0.721569,0.333333,0.388235,0.721569,0.611765,0.890196,0.721569,0.721569,
	0.556863,0.721569,0.666667,0.556863,0.611765,0.721569,0.721569,0.945098,0.721569,0.721569,0.611765,0.333333,0.278431,0.333333,0.470588,0.501961,
	0.333333,0.443137,0.501961,0.443137,0.501961,0.443137,0.333333,0.501961,0.501961,0.278431,0.278431,0.501961,0.278431,0.776471,0.501961,0.501961,
	0.501961,0.501961,0.333333,0.388235,0.278431,0.501961,0.501961,0.721569,0.501961,0.501961,0.443137,0.478431,0.2,0.478431,0.541176,0.721569,
	0.721569,0.721569,0.666667,0.611765,0.721569,0.721569,0.721569,0.443137,0.443137,0.443137,0.443137,0.443137,0.443137,0.443137,0.443137,0.443137,
	0.443137,0.443137,0.278431,0.278431,0.278431,0.278431,0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,0.501961,
	0.501961,0.4,0.501961,0.501961,0.501961,0.34902,0.454902,0.501961,0.760784,0.760784,0.980392,0.333333,0.333333,0.54902,0.890196,0.721569,
	0.713725,0.54902,0.54902,0.54902,0.501961,0.576471,0.494118,0.713725,0.823529,0.54902,0.27451,0.27451,0.309804,0.768627,0.666667,0.501961,
	0.443137,0.333333,0.564706,0.54902,0.501961,0.54902,0.611765,0.501961,0.501961,1,0.25098,0.721569,0.721569,0.721569,0.890196,0.721569,
	0.501961,1,0.443137,0.443137,0.333333,0.333333,0.54902,0.494118,0.501961,0.721569,0.168627,0.745098,0.333333,0.333333,0.556863,0.556863,
	0.501961,0.25098,0.333333,0.443137,1,0.721569,0.611765,0.721569,0.611765,0.611765,0.333333,0.333333,0.333333,0.333333,0.721569,0.721569,
	0.788235,0.721569,0.721569,0.721569,0.721569,0.278431,0.333333,0.333333,0.333333,0.333333,0.333333,0.333333,0.333333,0.333333,0.333333,0.333333
	},
	_maxTimesCharWidth = 0.980392;

/*---------------------------------------------------------------------------------------------------- */

void			check_pointer	(void*);

/*---------------------------------------------------------------------------------------------------- */

struct  avl_table *   uniqueTags   = NULL;

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
} * treeLabelWidths,
  * nodeCountsByLevel,
  * leafCountsByLevel;

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

void reportError (FILE* f,const char * err, long cci)
{
	char buffer[33];
	fprintf (stderr, "ERROR: %s. Tree string position %d\n", err, cci);
	fprintf (stderr, "?");
	buffer[fread  (buffer,1,32,f)] = 0;
	fprintf (stderr, "%s\n", buffer);
	exit (1);
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

long popValueFromVector (struct vector * v)
{
	if (v->vLength)
		return v->vData[--v->vLength];

	return 0;
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
		   childrenCount,
		   length;
		   
	struct vector   * children;
	
} *globalTreeRoot;

/*---------------------------------------------------------------------------------------------------- */

struct treeNode * allocateNewTreeNode (void)
{
	struct treeNode *newN = (struct treeNode*)malloc (sizeof (struct treeNode));
	check_pointer (newN);
	newN->parent = NULL;
	newN->startIndex		= 0;
	newN->length			= 0;
	newN->hitCount			= 0;
	newN->childrenCount		= 0;
	newN->children = allocateNewVector();
	check_pointer (newN->children);
	return newN;
}

/*---------------------------------------------------------------------------------------------------- */
void addAChild (struct treeNode* p, struct treeNode * c)
{
	long i = 0; 
	for (; i<p->children->vLength; i++)
		if (((struct treeNode**)p->children->vData)[i] == c)
			break;
	if (p->children->vLength == i)
	{
		appendValueToVector (p->children, (long)c);
		c->parent = p;
	}
}

/*---------------------------------------------------------------------------------------------------- */

void	destroyTreeNode (struct treeNode* n)
{
	free (n->children);
	free (n);
}

/*---------------------------------------------------------------------------------------------------- */

long	traverseTree (struct treeNode* n, long maxDepth, long currentDepth, long* height, long *depth)
{
	long			i = 0;
	double			w = 0.;
	char			buffer[255];
	
	if (currentDepth <= maxDepth)
	{
		if (currentDepth > *depth)
			*depth = currentDepth;
		
		if (currentDepth >= treeLabelWidths->vLength)
		{
			appendValueToVector (treeLabelWidths, 0);
			appendValueToVector (nodeCountsByLevel,0);
			appendValueToVector (leafCountsByLevel,0);
		}
	
		if (n->children->vLength)
		{
			nodeCountsByLevel->vData[currentDepth] ++;
			//fprintf (stdout, "%d %d %d\n", currentDepth, maxDepth, *height);

			if (currentDepth == maxDepth)
				(*height) ++;
			for (i=0; i<n->children->vLength; i++)
				n->childrenCount += traverseTree (((struct treeNode**)n->children->vData)[i], maxDepth, currentDepth+1,height,depth);
		}
		else
		{
			leafCountsByLevel->vData[currentDepth] ++;
			(*height) ++;
			n->childrenCount = countDuplicateTaxID?n->hitCount:1;
		}

		sprintf (buffer,":%d", n->childrenCount);

		for (i=0; i<n->length; i++)
			w += _timesCharWidths[*(globalNameBuffer->sData + n->startIndex + i)]; 
		for (i=0; buffer[i]; i++)
			w += _timesCharWidths[buffer[i]]; 
		
		w *= fontSize;
		w += 0.5;
		
		if (w > treeLabelWidths->vData[currentDepth])
			treeLabelWidths->vData[currentDepth] = w;		
	}
	else
	{
		if (n->children->vLength)
			for (i=0; i<n->children->vLength; i++)
				n->childrenCount += traverseTree (((struct treeNode**)n->children->vData)[i], maxDepth, currentDepth+1,height,depth);
		else
			n->childrenCount = countDuplicateTaxID?n->hitCount:1;
	}
	return n->childrenCount;
}

/*---------------------------------------------------------------------------------------------------- */
void	drawGradient (FILE* f, double left, double top, double right, double bottom)
{
	double color = 0.,
		   step  = 1./(right-left),
		   i     = left;
	
	fprintf (f, "currentlinewidth 1 setlinewidth \n");
	for (i=left; i<right; i+=1.0)
	{
		color = step*(i-left);
		fprintf (f, "%g %g %g setrgbcolor \n", 1.-color*color*color, 0.5*color, color ); 
		fprintf (f, "newpath %g %g moveto %g %g lineto stroke\n",i,top,i,bottom);
	}
	
	fprintf (f, "0 0 0 setrgbcolor %g %g %g %g rectstroke setlinewidth\n",left, top, right-left, bottom-top);
	fprintf (f, "%g %g (100\\%%) centertext\n", left, bottom - fontSize-2);
	fprintf (f, "%g %g (50\\%%) centertext\n", 0.5*(left+right), bottom - fontSize-2);
	fprintf (f, "%g %g (0\\%%) centertext\n", right, bottom - fontSize-2);
}

/*---------------------------------------------------------------------------------------------------- */
void	drawPSLine (FILE* f, double left, double top, double right, double bottom, double lineWidth, double color)
{
	//color  = sin(color*0.5*3.14);
	fprintf (f, "%g %g %g setrgbcolor \n", 1.-color*color*color, 0.5*color, color); 
	if (lineWidth > 0.)
		fprintf (f, "%g setlinewidth ");
	fprintf (f, "newpath %g %g moveto %g %g lineto stroke\n",left,top,right,bottom);
}

/*---------------------------------------------------------------------------------------------------- */
void	drawTextInAbox (FILE* f, long from, long to, long childrenCount, double x, double y)
{
	long i;
	
	fprintf (f, "newpath %g %g moveto (", x,y);
	if (from>=0)
		for (i=from; i<to; i++)
			fputc (globalNameBuffer->sData[i],f);
	else
		fprintf (f,"N/A");
	fprintf (f, ":%d) drawletter\n", childrenCount);	
}

/*---------------------------------------------------------------------------------------------------- */
void	drawTextInAbox2 (FILE* f, long splits, long childrenCount, long level, double x, double y)
{
	long i;
	
	fprintf (f, "newpath %g %g moveto (%d %s", x,y, splits, level<NUMBER_OF_TAX_FIELDS?rankLabels[level]:"n/a");
	fprintf (f, ":%d) drawletter2\n", childrenCount);	
}


/*---------------------------------------------------------------------------------------------------- */

double	traverseTreePS (FILE* f, struct treeNode* n, long maxDepth, long currentDepth, double parentX, double* currentLeafY, double* childX)
{
	double  myX,
			myY,
			minChildY = 0.,
			maxChildY = 0.,
			t;
		
	long i;
		 
	if (currentDepth <= maxDepth)
	{
		if (currentDepth)
			myX = parentX + treeLabelWidths->vData[currentDepth-1] + xPadding;
		else
			myX = parentX;
		
		if (n->children->vLength && maxDepth > currentDepth)
		{
			minChildY = traverseTreePS (f,((struct treeNode**)n->children->vData)[0], maxDepth, currentDepth+1,myX,currentLeafY,&t);
			drawPSLine (f, myX, minChildY, t, minChildY,-1., 1. - ((struct treeNode**)n->children->vData)[0]->childrenCount * countScaler);
			for (i=1; i<n->children->vLength-1; i++)
			{
				maxChildY = traverseTreePS (f,((struct treeNode**)n->children->vData)[i], maxDepth, currentDepth+1,myX,currentLeafY,&t);
				drawPSLine (f, myX, maxChildY, t, maxChildY,-1.,1. - ((struct treeNode**)n->children->vData)[i]->childrenCount * countScaler);
			}
			if (i<n->children->vLength)
			{
				maxChildY = traverseTreePS(f,((struct treeNode**)n->children->vData)[i], maxDepth, currentDepth+1,myX,currentLeafY,&t);
				drawPSLine (f, myX, maxChildY, t, maxChildY,-1.,1. - ((struct treeNode**)n->children->vData)[i]->childrenCount * countScaler);
			}
			else
				maxChildY = minChildY;
				
			if (maxChildY > minChildY)
			{
				drawPSLine (f, myX, minChildY, myX, maxChildY,-1.,1.-n->childrenCount * countScaler);				
			}
				
			myY = (minChildY+maxChildY)*0.5;
		}
		else
		{
			myY = *currentLeafY;
			*currentLeafY += ySpacing;	
		}
		//fprintf (stdout, "%d %d\n", n->startIndex, n->length);
		if (!(n->length == 1 && globalNameBuffer->sData[n->startIndex] == 'n'))
			drawTextInAbox (f, n->startIndex, n->startIndex+n->length, n->childrenCount, myX, myY-fontSize/2);
		else
		{
			if (n->children->vLength)
			{
				if (currentDepth == maxDepth)
				{
					i = currentDepth;
					while (n->children->vLength == 1)
					{
						n = ((struct treeNode**)n->children->vData)[0];
						i++;
					}
					if (!(n->length == 1 && globalNameBuffer->sData[n->startIndex] == 'n'))
						drawTextInAbox  (f, n->startIndex, n->startIndex+n->length, n->childrenCount, myX, myY-fontSize/2);
					else
						drawTextInAbox2 (f, n->children->vLength, n->childrenCount, i, myX, myY-fontSize/2);	
				}
			}
			else
				drawTextInAbox (f, -1, 0, n->childrenCount, myX, myY-fontSize/2);
			
		}
	}	 
	
	*childX = myX;
	return myY;
}

/*---------------------------------------------------------------------------------------------------- */
/*---------------------------------------------------------------------------------------------------- */

struct		storedSequenceTag
{
	long		startIndex,
				length;
};

/*---------------------------------------------------------------------------------------------------- */

struct storedSequenceTag *allocateStringTag (void)
{
	struct storedSequenceTag *newS = (struct storedSequenceTag*)malloc (sizeof (struct storedSequenceTag));
	check_pointer (newS);
	newS->startIndex  = -1;
	newS->length	  = 0;
	return newS;
}

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
	struct  storedSequenceTag		*sTag  = allocateStringTag(),
									*sTag2 = allocateStringTag(),
									*sTag3;
									
	struct  avl_traverser			avlt;
																
	struct  treeNode				*currentParent = NULL,
									*currentNode;
									
	struct  vector					*nodeStack = allocateNewVector();
									
	char	automatonState			= 0,
			currentChar				= 0,
			buffa					[255];
			
	double  Ycoord = 0.0,
			Xcoord = 0.0,
			t;
						
	long	currentCharID			= 0,
			indexer,
			indexer2,
			indexer3,
			maxTreeLevel			= 0,
			branchWeight			= 0;
			
	FILE  	* psFile				= NULL,
			* inFile				= NULL;
						
	globalNameBuffer  = allocateNewString();			
	check_pointer	  (uniqueTags		  = avl_create (compare_tags, NULL, NULL));
	
 	for (indexer = 0; indexer < 256; indexer ++)
		validTaxonNameChar[indexer] = 1;
		
	validTaxonNameChar[','] = 0;
	validTaxonNameChar[')'] = 0;
	validTaxonNameChar['('] = 0;
	validTaxonNameChar[':'] = 0;

   if (argc != 7)
    {
		fprintf (stderr,"%s",Usage);
        return 1;
    }
	
	maxTreeLevel   = atoi  (argv[3]);
	if (maxTreeLevel < 1)
		maxTreeLevel = 0xfffffffL;
		
    inFile		   = fopen (argv[1], "rb"); 
	if (!inFile)
	{
		fprintf (stderr, "Failed to open the input file %s\n", argv[1]);
		return 1;
	}

	psFile		   = fopen (argv[2], "wb"); 
	if (!psFile)
	{
		fprintf (stderr, "Failed to open the tree output file %s\n", argv[2]);
		return 1;
	}
	
	fontSize = atoi (argv[4]);
	if (fontSize < 2)
		fontSize = 2;
	if (fontSize > 255)
		fontSize = 255;
		
	 showMaxNodes = atoi (argv[5]);
	 if (showMaxNodes <= 0)
	 	showMaxNodes = 0x7FFFFFFFL;

	 countDuplicateTaxID = atoi (argv[6]);

	 ySpacing		 = fontSize+2*lineWidth + 5;
	 xPadding		 = fontSize*2;
	 globalXPad		 = fontSize;
	 globalYPad		 = fontSize*3/2;
	
	currentChar  = fgetc(inFile);
	while (1)
	{	
		currentCharID ++;
		//fprintf (stderr, "%d %c %d %d\n", currentCharID, currentChar, automatonState,nodeStack->vLength);
		switch (automatonState)
		{
			case 0: /* waiting for the opening '(' */
				if (currentChar == '(')
				{
					automatonState 			= 1; /* create new node*/
					globalTreeRoot 			= allocateNewTreeNode();
					appendValueToVector 	(nodeStack, (long)globalTreeRoot);
					currentChar 			= fgetc(inFile);
				}
				break;
				
			case 1: /* starting node read; first pass */
			case 8: /* starting node read */
			{
				if (currentChar == ',')
				{
					if (automatonState == 1)
						reportError (inFile,"empty first clade node name", currentCharID);
						
					currentNode 			= allocateNewTreeNode();
					appendValueToVector 	(nodeStack, (long)currentNode);
					automatonState			= 8;
					currentChar 			= fgetc(inFile);
				}
				else
				{
					if (currentChar == ')')
					{
						automatonState = 2;	
						currentChar 			= fgetc(inFile);
					}
					else
					{
						if (currentChar == '(')
						{
							currentNode 			= allocateNewTreeNode();
							appendValueToVector 	(nodeStack, (long)currentNode);
							currentChar 			= fgetc(inFile);
							//automatonState			= 1;
						}
						else
						{
							if (automatonState == 1)
							{
								currentNode 			= allocateNewTreeNode();
								appendValueToVector 	(nodeStack, (long)currentNode);
							}
							currentCharID--;
							automatonState = 2;
						}
					}
				}
				break;
			}	
			case 2: /* reading first node character */
				{
					if (!validTaxonNameChar[currentChar])
						reportError (inFile,"empty node name", currentCharID);
					sTag->startIndex 		= globalNameBuffer->sLength;
					sTag->length = 1;
					appendCharacterToString  (globalNameBuffer, currentChar);
					automatonState 			= 3;
					currentChar 			= fgetc(inFile);
				}
				break;

			case 3: /* reading additional node characters */
				{
					if (validTaxonNameChar[currentChar])
					{
						sTag->length++;
						appendCharacterToString  (globalNameBuffer, currentChar);
						currentChar 			= fgetc(inFile);						
					}
					else
					{
						if (currentChar == ':')
						{
							automatonState = 4; /* read branch length */
							currentChar 			= fgetc(inFile);						
						}
						else
						{
							currentCharID--;
							if (currentChar == ',' || currentChar == ')')
								automatonState = 6; /* finish up a node read */
							else
								reportError (inFile,"unexpected '(' character following a branch name", currentCharID);
						}
					}
				}
				break;
			case 4: /* initial read in branch length */
			{
				if (isnumber (currentChar))
				{
					automatonState    = 5;
					sTag2->startIndex = globalNameBuffer->sLength;
					sTag2->length     = 1;
					appendCharacterToString (globalNameBuffer,currentChar);
					currentChar 			= fgetc(inFile);						
				}
				else
					reportError (inFile,"expected a digit following ':'", currentCharID);
				break;
			}
			case 5: /* continued read branch length */
			{
				if (isnumber (currentChar))
				{
					sTag2->length++;
					appendCharacterToString (globalNameBuffer,currentChar);
					currentChar 			= fgetc(inFile);						
				}
				else
				{
					currentCharID --;
					if (currentChar == ',' || currentChar == ')')
						automatonState = 6; /* finish up a node read */
					else
						reportError (inFile,"expected a ',' or a ')' following a branch length", currentCharID);
				}
				break;
			}
			case 6: /* create a new node with a name and a branch length */
			{
				currentNode 			= (struct treeNode*) popValueFromVector (nodeStack);
				if (!currentNode)
					reportError (inFile,"incorrect tree structure", currentCharID);
					
				if (sTag2->length)
				{
					//fprintf (stderr, "%d %s\n", sTag2->length, globalNameBuffer->sData+sTag2->startIndex);
					currentNode->hitCount = atoi (globalNameBuffer->sData+sTag2->startIndex);
					globalNameBuffer->sLength -= sTag2->length;
					globalNameBuffer->sData[globalNameBuffer->sLength] = 0;
				}
				sTag3 = *(struct storedSequenceTag**)avl_probe (uniqueTags,sTag);
				if (sTag == sTag3) // new node
					sTag = allocateStringTag();
				else
				{
					//fprintf (stderr, "%d %s\n", sTag->length, globalNameBuffer->sData+sTag->startIndex);
					globalNameBuffer->sLength -= sTag->length;
					globalNameBuffer->sData[globalNameBuffer->sLength] = 0;
					//fprintf (stderr, "Duplicate %s %d %d %d\n", globalNameBuffer->sData,globalNameBuffer->sLength, 
					//				sTag3->startIndex,  sTag3->length);
				}
				currentNode->startIndex = sTag3->startIndex;
				currentNode->length     = sTag3->length;
					
				if (nodeStack->vLength) // add current node to the parent
					addAChild ((struct treeNode*) nodeStack->vData[nodeStack->vLength-1],currentNode);
				else
					if (currentNode != globalTreeRoot)
						reportError (inFile,"imbalanced paretheses: too many closing ')'", currentCharID);
					else	
						//if (feof (inFile))
						{
							automatonState = 1;
							break;
						}
				currentCharID--;
				//currentChar 			= fgetc(inFile);
				automatonState          = 8; // go back to reading more nodes
			}
			break;
		}
		if (feof (inFile))
			if (automatonState == 3 || automatonState == 5)
				automatonState = 6;
			else
				break;
	}

    if (automatonState != 1)
		reportError (inFile,"imbalanced paretheses in the tree", currentCharID);
		
	indexer = 0; indexer2 = 0; indexer3 = 0;
	treeLabelWidths   = allocateNewVector();
	nodeCountsByLevel = allocateNewVector();
	leafCountsByLevel = allocateNewVector();
	 
	traverseTree     (globalTreeRoot, maxTreeLevel, 0, & indexer, & indexer2);	
	//fprintf (stdout, "Height:%d Depth:%d\n", indexer, indexer2);
	
	Xcoord = 0;
	for (indexer3 = 0; indexer3 < treeLabelWidths->vLength; indexer3++)
		if (Xcoord < treeLabelWidths->vData[indexer3])
			Xcoord = treeLabelWidths->vData[indexer3];
		
	t = 16 * _maxTimesCharWidth * fontSize + 0.5;
	if (t>Xcoord)
		treeLabelWidths->vData[treeLabelWidths->vLength-1] = t;
	else
		treeLabelWidths->vData[treeLabelWidths->vLength-1] = Xcoord;
		
	Xcoord = globalXPad;
	for (indexer3 = 1; indexer3 < leafCountsByLevel->vLength; indexer3++)
		leafCountsByLevel->vData[indexer3] += leafCountsByLevel->vData[indexer3-1];

	for (indexer3 = 0; indexer3 < treeLabelWidths->vLength; indexer3++)
	{
		//fprintf (stdout, "Level %d, nodes %d\n", indexer3, nodeCountsByLevel->vData[indexer3] + leafCountsByLevel->vData[indexer3]);
		if (nodeCountsByLevel->vData[indexer3] + leafCountsByLevel->vData[indexer3] > showMaxNodes && indexer3 < maxTreeLevel)
		{
			maxTreeLevel = indexer3-1;
			indexer = nodeCountsByLevel->vData[maxTreeLevel] + leafCountsByLevel->vData[maxTreeLevel];
			break;
		}
		Xcoord += treeLabelWidths->vData[indexer3] + xPadding;
	}
	Ycoord = 3.*globalYPad + indexer * ySpacing;
	
	countScaler = 1./(countDuplicateTaxID?globalTreeRoot->hitCount:globalTreeRoot->childrenCount);
	
	fprintf (psFile,"%% PS file for the tree '%s'.\n%% Generated by tree2PS on %s\n<< /PageSize [%d %d] >> setpagedevice\n %g setlinewidth\n1 setlinecap\n",
					argv[1], argv[1], 
					(long)(Xcoord+0.5), (long)(Ycoord+0.5), lineWidth);
	fprintf (psFile, "/Times-Roman findfont %d scalefont\nsetfont\n",fontSize);
	fprintf (psFile,"/drawletter  {2 0 rmoveto 1 copy false charpath pathbbox 2 index 3 sub sub exch 3 index 3 sub sub exch  0.85 setgray 4 copy rectfill 0 setgray  3 index 3 index currentlinewidth 0.5 setlinewidth 7 3 roll rectstroke setlinewidth exch 1.5 add exch 1.5 add moveto show} def\n/centertext {dup newpath 0 0 moveto false charpath closepath pathbbox pop exch pop exch sub 2 div 4 -1 roll exch sub 3 -1 roll newpath moveto show} def\n");
	fprintf (psFile,"/drawletter2 {2 0 rmoveto 1 copy false charpath pathbbox 2 index 3 sub sub exch 3 index 3 sub sub exch  1 0.5 0 setrgbcolor 4 copy rectfill 0 setgray  3 index 3 index currentlinewidth 0.5 setlinewidth 7 3 roll rectstroke setlinewidth exch 1.5 add exch 1.5 add moveto show} def\n/centertext {dup newpath 0 0 moveto false charpath closepath pathbbox pop exch pop exch sub 2 div 4 -1 roll exch sub 3 -1 roll newpath moveto show} def\n");

	t = globalXPad*2. + 100. + 2*fontSize;
	drawGradient (psFile, globalXPad*2., Ycoord - 0.5*globalYPad, t<Xcoord ? t : Xcoord, Ycoord - globalYPad*1.5);

	Ycoord			  = globalYPad;
	traverseTreePS     (psFile, globalTreeRoot, maxTreeLevel, 0, globalXPad, &Ycoord, &Ycoord);	

	fclose  (inFile);
	fclose  (psFile);
	return   0;
}

