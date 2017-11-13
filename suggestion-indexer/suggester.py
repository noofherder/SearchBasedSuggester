#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import requests


SEARCH_URL = "http://localhost:9200/music_suggest/_search"


def make_main_query(partial, meta_filter):
    return {
        "query": {
            "bool": {
                "must": {
                    "function_score": {
                        "query": {
                            "dis_max": {
                                "tie_breaker": 0.5,
                                "queries": [{
                                    "prefix": {
                                        "suggestion.kw": {
                                            "value": partial,
                                            "boost": 100.0
                                        }
                                }}, {
                                    "match_phrase_prefix": {
                                        "suggestion": {
                                            "query": partial,
                                            "slop": 2,
                                            "boost": 10.0
                                        }
                                }}, {
                                    "match": {
                                        "suggestion": {
                                            "query": partial,
                                            "minimum_should_match": 1
                                        }
                                }}]
                            }
                        },
                        "boost_mode": "multiply",
                        "field_value_factor": {
                            "field": "freq",
                            "missing": 1,
                            "modifier": "log"
                        }
                    }
                },
                "filter": {
                    "bool": {
                        "must": [
                            {   "range": {
                                    "length": { "gte": len(partial) }
                            }},
                            meta_filter
                        ]
                    }
                }
            }
        },
        "size": 20,
        "_source": [ "suggestion" ]
    }

def make_meta_filter(min_viewcount, min_answercount):
    return {
        "nested": {
            "path": "meta",
            "query": {
                "bool": {
                    "must": [{
                        "range": {
                            "meta.viewcount": { "gte": min_viewcount }
                    }}, {
                        "range": {
                            "meta.answercount": { "gte": min_answercount }
                    }}]
                }
            }
        }
    }

def get_suggestions(partial, min_viewcount, min_answercount):
    query = make_main_query(partial, make_meta_filter(min_viewcount, min_answercount))
    response = requests.post(SEARCH_URL, data=json.dumps(query))
    response.raise_for_status()
    return [hit["_source"]["suggestion"] for hit in response.json()["hits"]["hits"]]

def main():
    suggestions = get_suggestions(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
    for sugg in suggestions:
        print sugg

if __name__ == "__main__":
    main()
