from fastapi import FastAPI, HTTPException, Body, Request, Response, Header
from rdflib import Graph
import json
import os
from pyshacl import validate

DATA_FILE = "../policies.json"
EVAL_LOG_FILE = "../evaluation_log.json"
DATA_GRAPH = "output.ttl"
TOKENS_FILE = "tokens.json"
STATUS_FILE = "../status.json"
SHACL_SHAPES_FILE = "astrea-shapes.ttl"
def initialice_graph():
    g = Graph()
    g.parse(DATA_GRAPH, format="turtle")
    return g


def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as file:
                return json.load(file)
        return {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar los datos: {str(e)}")



def save_data(data, g):
    for policy in data.values():
        g.parse(data=json.dumps(policy), format="json-ld")
    conforms, report = validate_policy(g)
    if not conforms:
        raise HTTPException(status_code=400, detail=f"SHACL validation failed:\n{report}")
    g.serialize(destination=DATA_GRAPH, format="turtle")
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)


def save_evaluation_log(evaluation_log):
    with open(EVAL_LOG_FILE, "a") as file:
        json.dump(evaluation_log, file)
        file.write("\n")


def check_content(request):
    print("new version: 1.0")
    if "Accept" in request.headers:
        response_format = request.headers["Accept"]
        if response_format != "application/ld+json" and response_format != "application/json":
            raise HTTPException(status_code=400, detail="Unsupported MIME type, only supported application/ld+json")
    if "Content-Type" in request.headers:
        request_format = request.headers["Content-Type"]
        if request_format != "application/ld+json" and request_format != "application/json":
            raise HTTPException(status_code=400, detail="Unsupported MIME type, only supported application/ld+json")

def validate_policy(data_graph: Graph):
    shapes_graph = Graph()
    shapes_graph.parse(SHACL_SHAPES_FILE, format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference='rdfs',
        abort_on_first=False,
        meta_shacl=False,
        debug=False
    )

    return conforms, results_text