import os
import re
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph

TRIPLESTORE_URL = os.getenv("TRIPLESTORE_URL", "http://fuseki:3030/ds")
DATA_GRAPH = os.getenv("GRAPH_FILE", "output.ttl")

def run_remote_sparql(query: str):
    sparql = SPARQLWrapper(f"{TRIPLESTORE_URL}/sparql")
    sparql.setReturnFormat(JSON)
    sparql.setMethod("POST")
    sparql.setQuery(query)
    return sparql.query().convert()

def run_local_sparql(query: str):
    g = Graph()
    g.parse(DATA_GRAPH, format="turtle")
    return [tuple(map(str, row)) for row in g.query(query)]

def execute(query: str):
    query = re.sub(r'(["\\])', r'\\\1', query)
    try:
        return {"mode": "remote", "data": run_remote_sparql(query)}
    except Exception:
        return {"mode": "local", "data": run_local_sparql(query)}
