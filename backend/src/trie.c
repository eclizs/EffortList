#include<stdio.h>
#include<stdlib.h>
#include<stdbool.h>
#include<string.h>
#include<ctype.h>
#include<regex.h>
#include "trie.h"

#ifdef DEBUG
    #define DEBUG_PRINT(fmt, ...) fprintf(stderr, "[%s:%d] " fmt, __func__, __LINE__, ##__VA_ARGS__)
#else
    #define DEBUG_PRINT(fmt, ...) ((void)0)
#endif

#define MAX_WORD_COUNT 1000
#define MAX_WORD_LENGTH 100

#define INDEXES 							\
		INDEX(WHITE_SPACE, ' ', 32, 26) 	\
		INDEX(FRONT_SLASH, '/', 47, 27) 	\
		INDEX(AT_SIGN, '@', 64, 28) 	\
		INDEX(DOUBLE_QUOTES, '"', 34, 29) 	\
		INDEX(COMMA, ',', 44, 30)			\
		INDEX(FRONT_BRACKETS, '(', 40, 31) 	\
		INDEX(BACK_BRACKETS, ')', 41, 32) 	\
		INDEX(PERIOD, '.', 46, 33) 			\
		INDEX(DIGIT_0, '0', 48, 34) 	\
		INDEX(DIGIT_1, '1', 49, 35) 	\
		INDEX(DIGIT_2, '2', 50, 36) 	\
		INDEX(DIGIT_3, '3', 51, 37) 	\
		INDEX(DIGIT_4, '4', 52, 38) 	\
		INDEX(DIGIT_5, '5', 53, 39) 	\
		INDEX(DIGIT_6, '6', 54, 40) 	\
		INDEX(DIGIT_7, '7', 55, 41) 	\
		INDEX(DIGIT_8, '8', 56, 42) 	\
		INDEX(DIGIT_9, '9', 57, 43)			\
		INDEX(HYPHEN, '-', 45, 44)			\
		INDEX(PLUS_SIGN, '+', 43, 45)
		//	    name   ,char,ascii,idx

int getNumChar() { return NUM_CHAR; }

bool wordIsValid(char* text)
{
	regex_t regex;

	const char* pattern = "^[-a-zA-Z0-9 /@\"()+.,]*$";

	regcomp(&regex, pattern, REG_EXTENDED);

	bool result;

	if(regexec(&regex, text, 0, NULL, 0) == 0) result = true;
	else result = false;

	regfree(&regex);
	return result;
}

static int getIdx(char letter)
{
	switch(letter)
	{
		#define INDEX(name, ch, ascii, idx) case ch: return idx;
		INDEXES
		#undef INDEX
	}
	if(letter < 97)
	{
		DEBUG_PRINT("ERROR: invalid character\n");
		exit(EXIT_FAILURE);
	}

	return (letter - 'a');
}

static char setChar(int index)
{
	switch(index)
	{
		#define INDEX(name, ch, ascii, idx) case idx: return ascii;
		INDEXES
		#undef INDEX
	}

	return (index + 'a');
}

static void toLowerCase(unsigned char* text)
{
	for(int i = 0; text[i] != '\0'; i++) text[i] = tolower(text[i]);
}

TrieNode *createTrieNode()
{
	TrieNode *newNode = (TrieNode*)calloc(1,sizeof(TrieNode));

	if(newNode == NULL)
	{
		DEBUG_PRINT("Memory allocation failed! Program will be terminated.\n");
		exit(EXIT_FAILURE);
	}
	
	return newNode;
}

int insertTrieNode(TrieNode **root, char *signedText)
{
	if(strlen(signedText) == 0) return 400;
	if(!wordIsValid(signedText)) return 422;
	if(*root == NULL) *root = createTrieNode(false);
	
	unsigned char *text = (unsigned char*)signedText;

	DEBUG_PRINT("DEBUG: text after converting to lowercase: %s\n", text);
	
	TrieNode *temp = *root;
	int length = strlen(signedText);
	DEBUG_PRINT("DEBUG: signedText: %s\n", signedText);
	
	for(int i = 0 ; i < length; i++)
	{
		text[i] = tolower(text[i]);

		int index = getIdx(text[i]);
		if(temp->children[index] == NULL)
			temp->children[index] = createTrieNode();
			
		temp = temp->children[index];
	}
	
	if(temp->terminal == true) return 409;
	else
	{
		temp->terminal = true;
		temp->original = strdup(signedText);;
	}
	
	return 201;
}

static void findWords_rec(TrieNode *node, unsigned char *buffer, int length, char** entries, int *counter)
{
	if(node == NULL)
	{
		DEBUG_PRINT("node is null\n");
		return;
	}
	if(*counter >= MAX_WORD_COUNT) return; // Prevent overflow of entries array
	
	if(node->terminal)
	{
		entries[*counter] = strdup(node->original);
		*counter += 1;
	}
	
	for(int i = 0; i < NUM_CHAR; i++)
	{
		if(node->children[i] != NULL)
		{
			buffer[length] = setChar(i);
			buffer[length+1] = '\0';
			DEBUG_PRINT("DEBUG: i=%d, buffer=%s\n", i, buffer);
			findWords_rec(node->children[i], buffer, length+1, entries, counter);
		}
	}
}

WordList findWords(TrieNode *root, char *signedPrefix) //wrapper function
{
	if(root == NULL)
	{
		DEBUG_PRINT("There is no slang word in the dictionary.\n");
		return (WordList){NULL, 0};
	}
	if(!wordIsValid(signedPrefix))
	{
		DEBUG_PRINT("Invalid word format\n");
		return (WordList){NULL, 0};
	}

	unsigned char buffer[MAX_WORD_LENGTH];

	TrieNode *node = NULL;
	int length;
	if(strlen(signedPrefix) > 0)
	{
		length = strlen(signedPrefix);
		memcpy(buffer, signedPrefix, length);
		buffer[length] = '\0';

		TrieNode *prefixNode = findPrefixNode(root, signedPrefix);
		unsigned char *prefix = (unsigned char*)signedPrefix;

		
		if(prefixNode == NULL) return (WordList){NULL, 0};
		
		DEBUG_PRINT("DEBUG: prefix=%s, length=%d\n", prefix, length);

		node = prefixNode;
	}
	else 
	{
		buffer[0] = '\0';
		node = root;
		length = 0;
	}
	DEBUG_PRINT("DEBUG: prefix=%s\n", buffer);

	int counter = 0;

	char** entries = (char**)calloc(MAX_WORD_COUNT, sizeof(char*));
	findWords_rec(node, buffer, length, entries, &counter);
	return (WordList)
	{
		.entries = entries,
		.count = counter
	};
}

TrieNode* findPrefixNode(TrieNode *root, char *signedPrefix)
{
	TrieNode *temp = root;
	int length = strlen(signedPrefix);
	unsigned char *prefix = (unsigned char*)signedPrefix;

	if(!wordIsValid(signedPrefix))
	{
		DEBUG_PRINT("word is not valid");
		return NULL;
	}
	
	DEBUG_PRINT("DEBUG: prefix=%s, length=%d\n", prefix, length);
	for(int i = 0; i < length; i++)
	{
		if(temp == NULL) return NULL;
		prefix[i] = tolower(prefix[i]);

		int index = getIdx(prefix[i]);
		DEBUG_PRINT("DEBUG: char=%c, index=%d\n", prefix[i], index);
		temp = temp->children[index];
	}
	
	if(temp != NULL) DEBUG_PRINT("DEBUG: temp is terminal: %d\n", temp->terminal);
	return temp;
}

bool nodeHasChildren(TrieNode *node)
{
	if(node == NULL) return false;

	for(int i = 0; i < NUM_CHAR; i++)
	{
		if(node->children[i] != NULL) return true;
	}
	return false;
}

static TrieNode* deleteWord_rec(TrieNode *node, unsigned char *text, bool *deleted)
{
	if(node == NULL) return node;

	if(*text == '\0')
	{
		if(node->terminal)
		{
			node->terminal = false;
			free(node->original);
			*deleted = true;

			if(!nodeHasChildren(node))
			{
				free(node);
				node = NULL;
			}
		}
		return node;
	}

	int index = getIdx(tolower(text[0]));
	node->children[index] = deleteWord_rec(node->children[index], text + 1, deleted);

	if(*deleted && !nodeHasChildren(node) && !node->terminal)
	{
		free(node);
		node = NULL;
	}
	return node;
}

bool deleteWord(TrieNode **root, char *signedText)
{
	if(*root == NULL || strlen(signedText) == 0 || !wordIsValid(signedText)) return false;
	unsigned char *text = (unsigned char*)signedText;
	bool result = false;

	*root = deleteWord_rec(*root, text, &result);
	return result;
}

void destroyTrieNode(TrieNode **root)
{
	if(*root == NULL) return;

	for(int i = 0; i < NUM_CHAR; i++)
	{
		if((*root)->children[i] != NULL)
			destroyTrieNode(&(*root)->children[i]);
	}

	if((*root)->original) free((*root)->original);
	free(*root);
	*root = NULL;
}

void freeWordList(WordList wordList)
{
	if(!wordList.entries) return;

	for(int i = 0; i < wordList.count; i++)
	{
		free(wordList.entries[i]);
	}
	free(wordList.entries);
}

// int main()
// {
// 	TrieNode *root = NULL;
// 	insertTrieNode(&root, "hello", "greeting");
// 	printTrieNode(root, "");
// 	printf("\n");

// 	TrieNode *test = findPrefixNode(root, "hello");

// 	Entry arrWords[10];
// 	findWords(root, "", arrWords);

// 	for (size_t i = 0; i < 3; i++)
// 	{
// 		printf("%s - %s\n", arrWords[i].word, arrWords[i].description);
// 	}
	
// 	printf("%d\n", test->terminal);
// 	if(test != NULL) printf("test is not null\n");
// 	if(test->terminal) printf("Found prefix node: %s\n", test->description);
// }