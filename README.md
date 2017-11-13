# SearchBasedSuggester

This is a proof of concept, using Elasticsearch, for search-based autosuggest which allows arbitrarily complex filtering.

The reason such a system might be useful is that the standard suggester components in Elasticsearch and Solr only have simple "context" filtering to control what suggestions are returned. In many cases, search engines implement access control logic based on the currently authenticated user. In general, the simple context filtering of the standard suggester is not able to model the access control of the main search.

Why do we care about access control for autosuggest? There are at least two reasons:

  * Suggestions may "leak" information about the content of the index to users who do not have access to sensitive documents. The simple fact that an index contains the word "redundancies", for example, may be significant.
  * If a user gets a suggestion for content they do not have access to, a search for that suggestion will return zero documents, which is unexpected and makes it look like the search engine is broken.

To be useful, suggesters must be fast, they must provide suggestions which make intuitive sense to the user and which, if followed, lead to search results, and they must be reasonably comprehensive (they should take account of all the content which the user potentially has access to.) For these reasons, it is impractical in most cases to implement suggestions directly from the search index.

This proof of concept demonstrates how an auxiliary suggestion index could be generated from a main search index, and how relevant suggestions could be retrieved from it, filtered by arbitrarily complex rules such as for implementing access control.

Each document in the suggestion index consists of a short fragment of text, from one to three words long. These correspond to word "shingles" in the source text, which do not span punctuation. For example, in the text:

  "All happy families are alike; each unhappy family is unhappy in its own way."

the shingles would include "families", "families are", "families are alike", but *not* "are alike each".

After this, any shingles containing at least one common "stopword" is rejected, so that the final remaining shingles from the text above are: "happy", "families", "happy families", "alike", "unhappy", and "unhappy family". This step is to reduce the size of the suggestion index and remove suggestions which are unlikely to prove useful.

The shingles are indexed along with the total frequency of their occurrence in the source corpus, and any metadata which is to be used for filtering. Since we may need to preserve relationships between metadata fields for meaningful filtering, they are indexed as Elasticsearch *nested objects* [1].

For the purposes of this proof of concept, I used the entire corpus of posts from the StackExchange Music forum [2], which is available as a free anonymised download [3].

## Creating the music index

## Creating the suggestions index

## Getting suggestions

## References

[1] https://www.elastic.co/guide/en/elasticsearch/reference/current/nested.html
[2] https://music.stackexchange.com/
[3] https://archive.org/details/stackexchange
