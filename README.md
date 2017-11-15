# SearchBasedSuggester

This is a proof of concept, using Elasticsearch, for search-based autosuggest which allows arbitrarily complex filtering.

The reason such a system might be useful is that the standard suggester components in Elasticsearch and Solr only have simple "context" filtering to control what suggestions are returned. In many cases, search engines implement access control logic based on the currently authenticated user. In general, the simple context filtering of the standard suggester is not able to model the access control of the main search.

Why do we care about access control for autosuggest? There are at least two reasons:

  * Suggestions may "leak" information about the content of the index to users who do not have access to sensitive documents. The simple fact that an index contains the word "redundancies", for example, may be significant.
  * If a user gets a suggestion for content they do not have access to, a search for that suggestion will return zero documents, which is unexpected and makes it look like the search engine is broken.

To be useful, suggesters must be fast, they must provide suggestions which make intuitive sense to the user and which, if followed, lead to search results, and they must be reasonably comprehensive (they should take account of all the content which the user potentially has access to.) For these reasons, it is impractical in most cases to implement suggestions directly from the search index.

This proof of concept demonstrates how an auxiliary suggestion index could be generated from a main search index, and how relevant suggestions could be retrieved from it, filtered by arbitrarily complex rules such as for implementing access control.

Each document in the suggestion index consists of a short fragment of text, from one to three words long. These correspond to word "shingles" (groups of concurrent words) in the source text, which do not span punctuation. For example, in the text:

> "All happy families are alike; each unhappy family is unhappy in its own way."

the shingles would include "families", "families are", "families are alike", but *not* "are alike each".

After this, any shingles containing at least one common "stopword" is rejected, so that the final remaining shingles from the text above are: "happy", "families", "happy families", "alike", "unhappy", and "unhappy family". This step is to reduce the size of the suggestion index and remove suggestions which are unlikely to prove useful.

The shingles are indexed along with the total frequency of their occurrence in the source corpus, and any metadata which is to be used for filtering. Since we may need to preserve relationships between metadata fields for meaningful filtering, they are indexed as Elasticsearch [*nested objects*][1].

For the purposes of this proof of concept, I used the entire corpus of posts from the [StackExchange Music forum][2], which is available as a free anonymised [download][3].

## Prerequisites

You need a fairly recent version of [Elasticsearch][4] (I used 5.5.1) installed and running. You also need [Python][5] 2.7.x with the [requests][6] module installed.

I wrote and tested the code on a Mac. It should work without modification on Linux. If you use Windows, you're on your own. ;)

## Creating the music index

To create the search index for the music corpus, download and uncompress the [zipped archive][3] (you may need to download a tool to deal with 7-zip files.) Then execute the following commands to create the index:
```
    cd test-index
    curl -XPUT localhost:9200/music -d@mappings.json
```
and index the music forum posts:
```
    ./indexer.py <path to unpacked posts archive>
```
To test that the index has been created correctly, run a search, e.g.:
```
    curl localhost:9200/music/_search?pretty\&q=piano
```

## Creating the suggestions index

The suggestions index is created by reading the entire music index in batches of 100, using the Elasticsearch [scroll API][7]. Shingles are extracted from the document text, and held in memory along with the access control metadata (in the music example we are using the fields *viewcount* and *answercount*.) The reason the shingles are held in memory is that until all the documents have been processed we don't have the entire set of document metadata to be indexed with each shingle. We also keep track of the frequency of each shingle, to be used later for ranking suggestions. Each record looks something like this:
```
    shingle: "playing funk guitar"
    frequency: 17
    metadata:
      - viewcount: 67
        answercount: 2
      - viewcount: 99
        answercount: 13
      - viewcount: 32
        answercount: 7
        ...
```
After all the source documents have been processed, the shingles and associated metadata are indexed to the suggestions index. To do this:
```
    cd suggestion-index
    curl -XPUT localhost:9200/music_suggest -d@mappings.json
    ./indexer.py
```

The shingle text is indexed both analysed (with the default analyser) and as a keyword. Metadata is indexed as nested objects.

## Getting suggestions

To get suggestions from the index, we run a normal Elasticsearch search. This consists of two main subqueries, joined by a *bool* query. First, there is the query to return a ranked list of suggestions (shingles). Second, there is a filter to only return suggestions that correspond to documents that the user is allowed to view. This is done with a *nested* query type, corresponding to the nested metadata objects in the index.

In the example python script, ```suggester.py```, the suggestion query consists of three subqueries in an attempt combine both [precision and recall][8]. First there is a *prefix* query against the keyword-indexed shingle, to try to get the closest match. Then there is a sloppy *match_phrase_prefix* query against the analysed field, to retrieve variations of the shingle. Finally there is a simple *match* query to catch whatever else might be available. These are boosted by 100, 10 and 1 respectively. The score is further boosted by the logarithm of the shingle frequency in the music index, to push more common shingles higher.

To run the suggester, supply the partially-completed user query and values for filtering by view count and answer count. For example:
```
    ./suggester.py "play gu" 100 10
```
which returns:
```
    play guitar
    play lead guitar
    already play guitar
    just play
    play along
    play chords
    ...
```

## Limitations

This is a first attempt at a proof of concept. The index mappings and query construction for the suggestions are almost certainly sub-optimal and could be improved with experimentation. This is probably also dependant on the topic domain.

The current implementation of the suggestions indexer cannot do incremental indexing for documents added, deleted or modified in the main index. Also, since it collates the suggestions in memory it might not be scalable to very large source indexes. It would certainly be possible to redesign the suggestions indexer to deal with these problems, though.

[1]: https://www.elastic.co/guide/en/elasticsearch/reference/current/nested.html
[2]: https://music.stackexchange.com/
[3]: https://archive.org/download/stackexchange/music.stackexchange.com.7z
[4]: https://www.elastic.co/downloads/elasticsearch
[5]: https://www.python.org/downloads/
[6]: http://docs.python-requests.org/en/master/user/install/
[7]: https://www.elastic.co/guide/en/elasticsearch/reference/current/search-request-scroll.html
[8]: https://en.wikipedia.org/wiki/Precision_and_recall
