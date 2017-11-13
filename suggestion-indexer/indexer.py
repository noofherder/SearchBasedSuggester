#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import requests
from HTMLParser import HTMLParser
import re
from stopwords import STOPWORDS

ES_URL = "http://localhost:9200/"
SOURCE_INDEX = "music"
SUGGESTION_INDEX = "music_suggest"
ALL_QUERY = "*:*"
SCROLL_TIME = "2m"

CHUNK_RE = re.compile(r'[\.\,\?\!\;\:]')
WORD_RE = re.compile(r"\w+(?:[\-\_\']+\w+)?")

TEXT_FIELDS = [ "body", "title" ]
META_FIELDS = [ "viewcount", "answercount" ]

MIN_WORD_LEN = 2
MAX_WORD_LEN = 30
MAX_SHINGLE_LEN = 3

class ShingleData:
    def __init__(self, shingle):
        self.shingle = shingle
        self.length = len(shingle)
        self.freq = 0
        self.metadata = {}

    def update(self, freq, metadata):
        self.freq += freq
        mdkey = hash(json.dumps(metadata, sort_keys=True))
        self.metadata.setdefault(mdkey, metadata)

def read_index(index):
    processed = 0
    shingle_data = {}

    # fetch 100 items from the index
    url = "{0}{1}/_search".format(ES_URL, SOURCE_INDEX)
    response = requests.get(url, params={
        "q": ALL_QUERY,
        "scroll": SCROLL_TIME,
        "size": 100
    })
    response.raise_for_status()
    respobj = response.json()
    hits = respobj['hits']['hits']
    process_documents(hits, shingle_data)
    processed += len(hits)

    # fetch more until we have processed them all
    while True:
        url = "{0}_search/scroll".format(ES_URL)
        body = json.dumps({
            "scroll_id": respobj["_scroll_id"],
            "scroll": SCROLL_TIME
        })
        response = requests.post(url, data=body)
        response.raise_for_status()
        respobj = response.json()
        hits = respobj['hits']['hits']
        if len(hits) == 0:
            break
        process_documents(hits, shingle_data)
        processed += len(hits)
        print "processed", processed, "docs, shingle_data size:", len(shingle_data), "\r",
        sys.stdout.flush()

    print
    return shingle_data

def process_documents(docs, shingle_data):
    for doc in docs:
        source =  doc["_source"]
        metadata = { field: source.get(field) for field in META_FIELDS
                     if source.get(field) }

        for field in TEXT_FIELDS:
            text = stripHTML(source.get(field, '').lower())
            for shin, freq in get_shingles(text).iteritems():
                shingle_data.setdefault(shin, ShingleData(shin)).update(freq, metadata)

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def stripHTML(text):
    s = MLStripper()
    s.feed(text)
    return s.get_data()

class RejectShingle(Exception):
    pass

def get_shingles(text):
    shingles = {}

    # extract shingles from within sentences and clauses
    for chunk in CHUNK_RE.split(text):
        words = WORD_RE.findall(chunk)
        for size in xrange(1, MAX_SHINGLE_LEN + 1):
            for i in xrange(len(words) + 1 - size):
                try:
                    shin = words[i:i + size]
                    for word in shin:
                        if len(word) < MIN_WORD_LEN or len(word) > MAX_WORD_LEN or word in STOPWORDS:
                            raise RejectShingle
                    shin = ' '.join(shin)
                    # increase the shingle freq
                    shingles[shin] = shingles.get(shin, 0) + 1
                except RejectShingle:
                    pass
    return shingles

def create_suggestion_index(shingle_data, index):
    batch = []
    for _id, item in enumerate(shingle_data.itervalues()):
        batch.append(json.dumps({
            "index": { "_index": index, "_type": "suggestion", "_id": _id }
        }))
        batch.append(json.dumps({
            "suggestion": item.shingle,
            "freq": item.freq,
            "length": item.length,
            "meta": item.metadata.values()
        }))

        if len(batch) == 100:
            index_batch(batch)
            batch = []
            print "indexed", _id, "of", len(shingle_data), "\r",
            sys.stdout.flush()

    if len(batch) > 0:
        index_batch(batch)

    print "\ndone"

def index_batch(batch):
    body = "\n".join(batch) + "\n"
    response = requests.post(ES_URL + "_bulk", data=body)
    response.raise_for_status()

def main():
    shingle_data = read_index(SOURCE_INDEX)
    create_suggestion_index(shingle_data, SUGGESTION_INDEX)

if __name__ == "__main__":
    main()
