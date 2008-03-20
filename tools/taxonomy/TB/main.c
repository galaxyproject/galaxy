#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>
#include <ctype.h>
#include <string.h>

#include "avl.h"

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

char	noValue[]   = "n\t",
		rootValue[] = "toor\t",
		usage[]		= "Incorrect number of arguments.\nExpected arguments: tax_id->label file, tax_id->hierarchy file, input file (gid taxid pairs), output file (24 columns)";

/*#define DEBUG_ME*/

/*---------------------------------------------------------------------------------------------------- */

void			check_pointer	(void*);

/*---------------------------------------------------------------------------------------------------- */

struct  avl_table *	nameTagAVL   = NULL,
				  * rankLabelAVL = NULL;

#define	DEFAULT_STRING_ALLOC	  16L

/*---------------------------------------------------------------------------------------------------- */

struct		bufferedString
{
	char *sData;
	long sLength,
		 saLength;
}
*globalNameBuffer;


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

void clear_buffered_string (struct bufferedString* theString)
{
	theString->sLength = 0;
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

struct		storedNameTag
{
	long		taxID,
				startIndex,
				length;
			
	char		taxonomy_level;
			
	struct		storedNameTag * parent;
};

/*---------------------------------------------------------------------------------------------------- */

struct storedNameTag * allocateNameTag (void)
{
	struct storedNameTag *newS = (struct storedNameTag*)malloc (sizeof (struct storedNameTag));
	check_pointer		(newS);
	newS->taxID				= 0;
	newS->startIndex		= 0;
	newS->length		    = 0;
	newS->parent		    = NULL;
	newS->taxonomy_level	= -1;
	return newS;
}

/*---------------------------------------------------------------------------------------------------- */

int compare_tags (const void *avl_a, const void *avl_b, void * xtra)
{
    long n1 = ((struct storedNameTag*)avl_a)->taxID;
    long n2 = ((struct storedNameTag*)avl_b)->taxID;
    
    if (n1 > n2) return 1;
    if (n1 < n2) return -1;
    return 0;
}

/*---------------------------------------------------------------------------------------------------- */

struct bufferedString * nameByID (long taxID)
{
	static struct			storedNameTag queryTag;
	struct storedNameTag *	res;
	struct bufferedString * resStr = NULL;
		
	queryTag.taxID = taxID;
	res = (struct storedNameTag *)avl_find(nameTagAVL, &queryTag);
	if (res)
	{
		resStr = allocateNewString();
		appendRangeToString(resStr,globalNameBuffer,res->startIndex,res->startIndex+res->length-1);
	}
	return resStr;
}

/*---------------------------------------------------------------------------------------------------- */

struct storedNameTag * tagByID (long taxID)
{
	static struct	storedNameTag queryTag;
	queryTag.taxID = taxID;
	return  (struct storedNameTag *)avl_find(nameTagAVL, &queryTag);
}

/*---------------------------------------------------------------------------------------------------- */

struct bufferedString * walkPath (long taxID)
{
	struct storedNameTag  * currentTag		= tagByID(taxID);
	if (!currentTag)
		return NULL;
		
	struct bufferedString * resStr			= allocateNewString();
	long   k, 
		   level = NUMBER_OF_TAX_FIELDS-1;
		   
	char  // buffer [32],
		   first_record = 1;
	
	while (currentTag) {
	
		if (currentTag->taxonomy_level >= 0)
		{
			if (first_record)
			{
				for (k = currentTag->taxonomy_level+1; k < NUMBER_OF_TAX_FIELDS; k++)
					appendCharBufferToString(resStr,noValue);
				first_record = 0;
			}
			else
			{
				for (k=currentTag->taxonomy_level+1; k<level; k++)
					appendCharBufferToString(resStr,noValue);
			}
			//appendCharacterToString(resStr,')');
			//sprintf (buffer, "%d", currentTag->taxonomy_level);
			//for (k=strlen(buffer)-1; k>=0; k--)
			//	appendCharacterToString(resStr,buffer[k]);
			//appendCharacterToString(resStr,'(');
			for (k=currentTag->startIndex+currentTag->length-1; k>=currentTag->startIndex; k--)
				appendCharacterToString(resStr,globalNameBuffer->sData[k]);
				
			appendCharacterToString(resStr,'\t');
			level		 = currentTag->taxonomy_level;
		}
		currentTag = currentTag->parent;
	}
	
	for (k = level-1; k ; k--)
		appendCharBufferToString(resStr,noValue);

	appendCharBufferToString(resStr,rootValue);

	return resStr;
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

int		compare_strings (struct bufferedString * s1, struct bufferedString * s2)
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

int		compare_tag_strings (const void *avl_a, const void *avl_b, void * xtra)
{
    struct storedNameTag* s1 = (struct storedNameTag*)avl_a;
    struct storedNameTag* s2 = (struct storedNameTag*)avl_b;
	char   *buffa			 = ((struct bufferedString*)xtra)->sData;

	long upTo,
		 i;
		 
	if  (s1->length>s2->length)
		upTo = s2->length;
	else
		upTo = s1->length;

	for (i=0; i<upTo; i++)
	{
		int res = (int)buffa[s1->startIndex+i]-buffa[s2->startIndex+i];
	 	if (res < 0)
	 		return -1;
	 	else
	 		if (res>0)
	 			return 1;
	}
	
	if (s1->length == s2->length)
		return 0;

	return 1-2*(s1->length<s2->length);
}



/*---------------------------------------------------------------------------------------------------- */

void destroy_string (struct bufferedString* aStr)
{
	free (aStr->sData);
	free (aStr);
}


/*---------------------------------------------------------------------------------------------------- */

void reportError (char * theMessage)
{
	fprintf (stderr, "\nERROR: %s\n", theMessage);
	exit (1);
}

/*---------------------------------------------------------------------------------------------------- */

void reportErrorLine (char * theMessage, long lineID)
{
	fprintf (stderr, "\nERROR in line %d: %s\n", lineID, theMessage);
	exit (1);
}


/*---------------------------------------------------------------------------------------------------- */

int main (int argc, const char * argv[]) 
{
    FILE							*inFile,
									*structFile,
									*queryFile,
									*outFile;
	
	struct	bufferedString			*scientificName = allocateNewString(),
									**currentBuffers,
									*qry;
									
	struct  storedNameTag			*aTag,
									*aTag2,
									*aTag3 = allocateNameTag();
									
	char	automatonState			= 0,
			currentField			= 0,
			currentChar				= 0,
			taxonBuffer				[1024],
			firstLine;
						
	long	currentLineID			= 1,
			expectedFields			= 4,
			indexer,
			indexer2;
			
			
	
   if (argc != 5)
    {
        fprintf (stderr,"%s\n", usage);
        return 1;
    }

	appendCharBufferToString(scientificName,	"scientific name");					
	globalNameBuffer = allocateNewString();			
	currentBuffers   = (struct	bufferedString**)malloc (expectedFields*sizeof (struct	bufferedString*));
	nameTagAVL		 = avl_create (compare_tags,	    NULL, NULL);
	rankLabelAVL	 = avl_create (compare_tag_strings, globalNameBuffer, NULL);
	
	for (indexer = 0; indexer < expectedFields; indexer++)
		currentBuffers[indexer] = allocateNewString();
		
	for (indexer = 0; indexer < NUMBER_OF_TAX_FIELDS; indexer++)
	{	
		aTag						= allocateNameTag   ();
		aTag->startIndex			= globalNameBuffer->sLength;
		appendCharBufferToString	 (globalNameBuffer,rankLabels[indexer]);
		aTag->taxonomy_level		= indexer;
		aTag->length				= strlen(rankLabels[indexer]);
		if ((aTag2 = *avl_probe(rankLabelAVL, aTag)) != aTag)
			reportErrorLine ("Duplicate taxonomic rank name", aTag2->taxonomy_level);
	}
		
		
 		
    inFile		= fopen (argv[1], "rb"); 
   
    if (!inFile)
    {
	   fprintf (stderr,"Failed to open input file: %s\n", argv[1]);
	   return 1; 
    }

    structFile		= fopen (argv[2], "rb"); 
   
    if (!structFile)
    {
	   fprintf (stderr,"Failed to open input file: %s\n", argv[2]);
	   return 1; 
    }
	
    queryFile		= fopen (argv[3], "rb"); 
   
    if (!queryFile)
    {
	   fprintf (stderr,"Failed to open input file: %s\n", argv[3]);
	   return 1; 
    }

	outFile		= fopen (argv[4], "w"); 
   
    if (!outFile)
    {
	   fprintf (stderr,"Failed to open output file: %s\n", argv[3]);
	   return 1; 
    }

	currentChar = fgetc(inFile);
	while (!feof(inFile))
	{
		switch (automatonState)
		{
			case 0: /* start of the line; expecting numbers */
				if (currentChar >= '0' && currentChar <='9')
				{
					automatonState = 1; /* reading sequence ID */
					appendCharacterToString(currentBuffers[currentField],currentChar);
				}
				else
					if (!(currentChar == '\n' || currentChar == '\r'))
						reportErrorLine ("Could not find a valid sequence ID to start the line",currentLineID);
				break;
				
			case 1: /* reading sequence ID */
				if (currentChar >= '0' && currentChar <='9')
					appendCharacterToString(currentBuffers[currentField],currentChar);
				else
					if (currentChar == '\t')
						automatonState = 2;
					else
						reportErrorLine ("Expected a tab following the tax ID",currentLineID);
					break;
					
			case 2: /* looking for a | */
				if (currentChar != '|')
					reportErrorLine ("Expected a '|' following the tab",currentLineID);
				else 
					automatonState = 3;
				break;
					
			case 3: /* looking for a \t or a \n|\r*/
				if (currentChar == '\t')
				{
					automatonState = 4;
					currentField   ++;
					if (currentField == expectedFields)
						reportErrorLine ("Too many fields",currentLineID);
				}
				else
					if (currentChar == '\n' || currentChar == '\r')
					{
						if (currentField < expectedFields-1) 
							reportErrorLine ("Too few fields",currentLineID);
						automatonState = 0;
						currentLineID ++;
						currentField = 0;
						if (compare_strings(currentBuffers[3],scientificName)==0)
						{
							aTag = allocateNameTag();
							aTag->taxID = atoi(currentBuffers[0]->sData);
							aTag->startIndex = globalNameBuffer->sLength;
							aTag->length	 = appendRangeToString(globalNameBuffer,currentBuffers[1],0,currentBuffers[1]->sLength-1);
							if (aTag->length <= 0)
								reportErrorLine ("Empty name tag",currentLineID);
							if (*avl_probe(nameTagAVL,aTag) != aTag)
								reportErrorLine ("Duplicate name tag",currentLineID);
							
						}
						for (indexer = 0; indexer < expectedFields; indexer++)
							clear_buffered_string(currentBuffers[indexer]);
					}
					else					
						reportErrorLine ("Expected a tab following the '|'",currentLineID);
				break;
				
			case 4: /* read a field */
				if (currentChar == '\t')
					automatonState = 2;
				else
					if (currentChar == '\n' || currentChar == '\r')
						reportErrorLine ("Unexpected end-of-line",currentLineID);
					else
						appendCharacterToString(currentBuffers[currentField],currentChar);
				break;
		
		}
		currentChar = fgetc(inFile);
	}

	fclose (inFile);
		
	for (indexer = 0; indexer < expectedFields; indexer++)
		destroy_string(currentBuffers[indexer]);

	free(currentBuffers);	
	expectedFields = 13;
	currentBuffers   = (struct	bufferedString**)malloc (expectedFields*sizeof (struct	bufferedString*));

	for (indexer = 0; indexer < expectedFields; indexer++)
		currentBuffers[indexer] = allocateNewString();
		
	automatonState = 0;
	currentLineID  = 1;
	currentField   = 0;
	
	currentChar = fgetc(structFile);

	while (!feof(structFile))
	{
		switch (automatonState)
		{
			case 0: /* start of the line; expecting numbers */
				if (currentChar >= '0' && currentChar <='9')
				{
					automatonState = 1; /* reading sequence ID */
					appendCharacterToString(currentBuffers[currentField],currentChar);
				}
				else
					if (!(currentChar == '\n' || currentChar == '\r'))
						reportErrorLine ("Could not find a valid sequence ID to start the line",currentLineID);
				break;
				
			case 1: /* reading sequence ID */
				if (currentChar >= '0' && currentChar <='9')
					appendCharacterToString(currentBuffers[currentField],currentChar);
				else
					if (currentChar == '\t')
						automatonState = 2;
					else
						reportErrorLine ("Expected a tab following the tax ID",currentLineID);
					break;
					
			case 2: /* looking for a | */
				if (currentChar != '|')
					reportErrorLine ("Expected a '|' following the tab",currentLineID);
				else 
					automatonState = 3;
				break;
					
			case 3: /* looking for a \t or a \n|\r*/
				if (currentChar == '\t')
				{
					automatonState = 4;
					currentField   ++;
					if (currentField == expectedFields)
						reportErrorLine ("Too many fields",currentLineID);
				}
				else
					if (currentChar == '\n' || currentChar == '\r')
					{
						if (currentField < expectedFields-1) 
							reportErrorLine ("Too few fields",currentLineID);
							
						aTag  = tagByID(atoi(currentBuffers[0]->sData));
						aTag2 = tagByID(atoi(currentBuffers[1]->sData));
						
						if (! (aTag && aTag2))
							reportErrorLine ("Invalid ID tag",currentLineID);
							
						if (aTag2 != aTag)
						{
							aTag->parent			= aTag2;
							aTag3->startIndex		= globalNameBuffer->sLength;
							aTag3->length			= currentBuffers[2]->sLength;
						    appendRangeToString		(globalNameBuffer, currentBuffers[2], 0, currentBuffers[2]->sLength-1);
							aTag2 = avl_find		(rankLabelAVL, aTag3);
							if (aTag2)
								aTag->taxonomy_level = aTag2->taxonomy_level;
							globalNameBuffer->sLength = aTag3->startIndex;
						}
						
						currentField = 0;
						automatonState = 0;
						currentLineID ++;
					
						for (indexer = 0; indexer < expectedFields; indexer++)
							clear_buffered_string(currentBuffers[indexer]);
					}
					else					
						reportErrorLine ("Expected a tab following the '|'",currentLineID);
				break;
				
			case 4: /* read a field */
				if (currentChar == '\t')
					automatonState = 2;
				else
					if (currentChar == '\n' || currentChar == '\r')
						reportErrorLine ("Unexpected end-of-line",currentLineID);
					else
						appendCharacterToString(currentBuffers[currentField],currentChar);
				break;
		
		}
		currentChar = fgetc(structFile);
	}

	fclose (structFile);

	for (indexer = 0; indexer < expectedFields; indexer++)
		destroy_string(currentBuffers[indexer]);
	free(currentBuffers);	
	expectedFields = 2;
	currentBuffers   = (struct	bufferedString**)malloc (expectedFields*sizeof (struct	bufferedString*));

	for (indexer = 0; indexer <= expectedFields; indexer++)
		currentBuffers[indexer] = allocateNewString();
		
	automatonState = 0;
	currentLineID  = 1;
	currentField   = 0;
	firstLine	   = 1;
	
	currentChar = fgetc(queryFile);

	while (!feof(queryFile))
	{
		switch (automatonState)
		{
			case 0: /* start of the line; expecting numbers */
				if (!isspace(currentChar))
				{
					automatonState = 1; /* reading sequence ID */
					appendCharacterToString(currentBuffers[currentField],currentChar);
				}
				else
					if (!(currentChar == '\n' || currentChar == '\r'))
						reportErrorLine ("Could not find a valid sequence ID to start the line",currentLineID);
				break;
				
			case 1: /* reading sequence ID */
				if ((currentField == 1 && currentChar >= '0' && currentChar <='9')||(currentField == 0 && currentChar != '\n' && currentChar != '\r' && currentChar != '\t'))
					appendCharacterToString(currentBuffers[currentField],currentChar);
				else
					if (currentChar == '\t')
					{
						automatonState = 1;
						currentField ++;
						if (currentField == expectedFields)
							automatonState = 2;
					}
					else
						if (currentChar == '\n' || currentChar == '\r')
						{
							currentField++;
							automatonState = 2;
							ungetc (currentChar,queryFile);
						}
						else
							reportErrorLine ("Expected a tab following a Tax/GID",currentLineID);
					break;
					
			case 2:
				if (currentChar == '\n' || currentChar == '\r')
				{
					if (currentField == expectedFields)
					{
						
						indexer2	= atoi (currentBuffers[1]->sData); // TaxID
						qry = walkPath (indexer2);
						if (firstLine)
							firstLine = 0;
						else
							fputc ('\n',outFile);
							
						fprintf (outFile,"%s\t%d", currentBuffers[0]->sData, indexer2);
						if (qry)
						{
							for (indexer = qry->sLength-1; indexer >= 0; indexer--)
								fputc (qry->sData[indexer], outFile);
							destroy_string(qry);
						}
						else
							fprintf (outFile, "\tNULL");
						if (currentBuffers[expectedFields]->sLength)
							fprintf (outFile, "\t%s", currentBuffers[expectedFields]->sData);

					}
					currentLineID ++;
					currentField = 0;
					for (indexer = 0; indexer <= expectedFields; indexer++)
						clear_buffered_string(currentBuffers[indexer]);
					automatonState = 0;
				}
				else
					appendCharacterToString(currentBuffers[currentField],currentChar);

		
		}
		currentChar = fgetc(queryFile);
	}

	fclose (structFile);
	fclose (queryFile);
	fclose (outFile);
	return 0;
}
