from fastapi import FastAPI, HTTPException, Body, Request, Response, Header
from fastapi.responses import JSONResponse
import secrets
from pydantic import BaseModel
from pyodre.odre import ODRE
from rdflib import Graph
import re
import json
import os
from fastapi.middleware.cors import CORSMiddleware

# from pydantic import BaseSettings
#
# class AppConfig(BaseSettings):
#     app_name: str
#     version: str
#     allowed_origins: list[str]
#     database_url: str
#     debug: bool
#
# with open("config.json") as config_file:
#     config_data = json.load(config_file)
#     config = AppConfig(**config_data)

app = FastAPI()
DATA_FILE = "../policies.json"
EVAL_LOG_FILE = "../evaluation_log.json"
DATA_GRAPH = "output.ttl"
TOKENS_FILE = "tokens.json"
STATUS_FILE = "../status.json"

g = Graph()
g.parse(DATA_GRAPH, format="turtle")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O especifica dominios como ["http://tu-dominio.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo datos
class Policy(BaseModel):
    odrl_policy: dict


# Persistencia
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    return {}


def save_data(data):
    for policy in data.values():
        g.parse(data=json.dumps(policy), format="json-ld")
    g.serialize(destination=DATA_GRAPH, format="turtle")
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)


def save_evaluation_log(evaluation_log):
    with open(EVAL_LOG_FILE, "a") as file:
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
    key_function = interpolations.get("key")
    if key_function not in FUNCTIONS_MAP:
        raise HTTPException(status_code=400, detail="Función no válida para 'key'")

    # Asignamos la función que debe ser utilizada para la interpolación
    selected_function = FUNCTIONS_MAP[key_function]
    interpolations["selected_function"] = selected_function

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
        raise HTTPException(status_code=404, detail="Policy not found")
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


@app.post("/api/update-data")
async def update_data(request: Request, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Token "):
        raise HTTPException(status_code=401, detail="Token no proporcionado o inválido")

    token = authorization.split(" ")[1]

    if not is_token_valid(token):
        raise HTTPException(status_code=403, detail="Token no autorizado")

    try:
        body = await request.json()
        policy_id = body.get("policy_id")
        status = body.get("status")

        if not policy_id or not status:
            raise HTTPException(status_code=400, detail="Datos incompletos")

        data = load_data()
        if policy_id not in data:
            raise HTTPException(status_code=404, detail="Política no encontrada")

        data[policy_id]["status"] = status
        save_data(data)

        return {
            "message": "Estado actualizado correctamente",
            "policy_id": policy_id,
            "new_status": status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar los datos: {str(e)}")

@app.get("/api/get-token")
async def get_token():
    token = secrets.token_hex(16)

    add_token(token)

    return JSONResponse(content={"token": token})


def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "r") as file:
            return json.load(file).get("valid_tokens", [])
    return []

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as file:
        json.dump({"valid_tokens": tokens}, file, indent=4)

def is_token_valid(token):
    return token in load_tokens()

def add_token(token):
    tokens = load_tokens()
    if token not in tokens:
        tokens.append(token)
        save_tokens(tokens)

def remove_token(token):
    tokens = load_tokens()
    if token in tokens:
        tokens.remove(token)
        save_tokens(tokens)


def status_var(key=None, id=None):
    """
    Verifica si el estado de una política coincide con el valor esperado.
    El valor esperado ya está contenido en la política, por lo que no es necesario pasarlo.
    """
    if not key or not id:
        raise ValueError("Los parámetros 'key' e 'id' son obligatorios")

    if not os.path.exists(STATUS_FILE):
        raise FileNotFoundError(f"El archivo de estados '{STATUS_FILE}' no existe")

    try:
        # Leer el archivo de estados
        with open(STATUS_FILE, "r") as file:
            statuses = json.load(file)

        # Buscar el estado de la política por su ID
        policy_status = statuses.get(id)
        if not policy_status:
            return False  # No se encontró la política con el ID dado

        # Obtener el valor actual de la clave
        current_value = policy_status.get(key)
        if current_value is None:
            raise ValueError(f"Clave '{key}' no encontrada en el estado de la política.")

        return current_value  # Se devuelve el valor actual, no una comparación directa con un valor esperado
    except Exception as e:
        raise RuntimeError(f"Error al verificar el estado: {str(e)}")


FUNCTIONS_MAP = {
    "status_var": status_var,  # Agrega otras funciones según sea necesario
    # "another_function": another_function,  # Ejemplo de otra función
}
