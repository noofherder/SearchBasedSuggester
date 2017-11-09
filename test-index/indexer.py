#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import xml.sax
import json
import requests

INDEX_NAME = "music"
INDEX_TYPE = "post"

INDEX_FIELDS = [ "Body", "Title", "CreationDate", "Score", "ViewCount", "AnswerCount",
                 "CommentCount", "FavoriteCount" ]

BATCH_URL = "http://localhost:9200/_bulk"
BATCH_SIZE = 2000

class StreamHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.batch = []

    def startElement(self, name, attrs):
        if name == "row":
            self.batch.append({ "index": { "_index": INDEX_NAME, "_type": INDEX_TYPE, "_id": attrs["Id"] }})
            self.batch.append({ field.lower(): attrs.get(field) for field in INDEX_FIELDS
                                if attrs.has_key(field) })
            if len(self.batch) == BATCH_SIZE:
                self.indexBatch()

    def endElement(self, name):
        if name == "posts" and len(self.batch) > 0:
            self.indexBatch()

    def indexBatch(self):
        body = "\n".join(json.dumps(row) for row in self.batch) + "\n"
        response = requests.post(BATCH_URL, data=body)
        response.raise_for_status()
        print "indexed", len(self.batch) / 2, "documents"
        self.batch = []

if __name__ == '__main__':
    parser = xml.sax.make_parser()
    parser.setContentHandler(StreamHandler())
    with open(sys.argv[1]) as f:
        parser.parse(f)
