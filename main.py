from fastapi import FastAPI, HTTPException, Body, Request, Response
from pydantic import BaseModel
from pyodre.odre import ODRE
from rdflib import Graph
import re
import json
import os

app = FastAPI()
data_file = "policies.json"
eval_log_file = "evaluation_log.json"
data_graph = "output.ttl"
g = Graph()
g.parse("output.ttl", format="turtle")


# Modelo datos
class Policy(BaseModel):
    odrl_policy: dict


# Persistencia
def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r") as file:
            return json.load(file)
    return {}


def save_data(data):
    for policy in data.values():
        g.parse(data=json.dumps(policy), format="json-ld")
    g.serialize(destination=data_graph, format="turtle")
    with open(data_file, "w") as file:
        json.dump(data, file, indent=4)


def save_evaluation_log(evaluation_log):
    with open(eval_log_file, "a") as file:
        json.dump(evaluation_log, file)
        file.write("\n")


# CRUD Endpoints
@app.post("/api/policy/", status_code=201)
async def create_policy(policy: Policy, response: Response, request: Request):
    check_content(request)
    data = load_data()
    policy_uid = policy.odrl_policy.get("uid").split(":")[-1]
    if not policy_uid:
        raise HTTPException(status_code=400, detail="La política debe tener un 'uid' como ID")
    if policy_uid in data:
        raise HTTPException(status_code=400, detail="ID ya existe")
    data[policy_uid] = policy.odrl_policy
    save_data(data)
    response.headers["Content-Type"] = "application/ld+json"
    return policy


@app.get("/api/policy/{id}")
async def get_policy(id: str):
    data = load_data()
    if id not in data:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    return data[id]


@app.get("/api/policy/")
async def get_policies():
    data = load_data()
    if not data:
        raise HTTPException(status_code=404, detail="No hay políticas almacenadas")
    return data


@app.delete("/api/policy/{id}")
async def delete_policy(id: str):
    data = load_data()
    if id not in data:
        raise HTTPException(status_code=404, detail="Política no encontrada")

    policy_uri = f"http://example.com/policy:{id}"
    g.remove((policy_uri, None, None))

    del data[id]
    save_data(data)
    return {"message": "Política eliminada"}


# Endpoint evaluar políticas
@app.get("/api/policy/evaluate/{id}")
async def evaluate_policy_id(id: str, request: Request):
    query_params = request.query_params

    interpolations = {key: query_params.get(key) for key in query_params.keys()}
    data = load_data()
    policy = data.get(id)
    if not policy:
        raise HTTPException(status_code=404, detail="Política no encontrada")

    try:
        odre = ODRE()
        evaluation_result = odre.enforce(policy=json.dumps(policy), interpolations=interpolations)

        evaluation_log = {
            "parameters": dict(request.query_params),
            "evaluation_result": evaluation_result
        }
        save_evaluation_log(evaluation_log)

        return evaluation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/policy/evaluate")
async def evaluate_policy(policy: Policy, request: Request):
    if not policy:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    check_content(request)
    query_params = request.query_params

    interpolations = {key: query_params.get(key) for key in query_params.keys()}
    try:
        odre = ODRE()
        evaluation_result = odre.enforce(policy=json.dumps(policy.dict()), interpolations=interpolations)

        evaluation_log = {
            "parameters": dict(request.query_params),
            "evaluation_result": evaluation_result
        }
        save_evaluation_log(evaluation_log)

        return evaluation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint consultas SPARQL
@app.post("/api/policy/sparql")
async def execute_sparql(body: dict = Body(...)):
    query = body.get('query')
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is missing")

    query = re.sub(r'(["\\])', r'\\\1', query)

    try:
        results = g.query(query)
        return {"query": query, "result": [str(result) for result in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# test junit
# test de escalabilidad
# test de evaluar con todas las de la demo de collab, tambien concurrentes, no se pueden las inyecciones de funciones
# todos gráfica de tiempos

def check_content(request):
    if "Accept" in request.headers:
        response_format = request.headers["Accept"]
        if response_format != "application/ld+json":
            raise HTTPException(status_code=400, detail="Unsupported MIME type, only supported application/ld+json")
    if "Content-Type" in request.headers:
        request_format = request.headers["Content-Type"]
        if request_format != "application/ld+json":
            raise HTTPException(status_code=400, detail="Unsupported MIME type, only supported application/ld+json")


def check_interpolation(policy):
    for permission in policy.get("permission", []):
        for constraint in permission.get("constraint", []):
            if "{{token}}" in constraint.get("leftOperand", ""):
                constraint["leftOperand"] = constraint["leftOperand"].replace("{{token}}", "valor_real")
