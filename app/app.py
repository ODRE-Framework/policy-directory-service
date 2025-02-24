from fastapi import FastAPI, HTTPException, Body, Request, Response, Header
from fastapi.responses import JSONResponse
import secrets
from pydantic import BaseModel
from pyodre.odre import ODRE
import re
import httpx
import traceback
from fastapi.middleware.cors import CORSMiddleware
from .services import *

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
import uvicorn

from fastapi.responses import RedirectResponse

app = FastAPI()

g = initialice_graph()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Policy(BaseModel):
    odrl_policy: dict


@app.get("/", response_class=RedirectResponse)
async def redirect_fastapi():
    return "/api/policy"


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
    save_data(data, g)
    response.headers["Content-Type"] = "application/ld+json"
    return policy


@app.get("/api/policy/{id}")
async def get_policy(id: str):
    data = load_data()
    if id not in data:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    return data[id]


@app.get("/api/policy/")
async def get_policies(response: Response):
    data = load_data()
    if not data:
        raise HTTPException(status_code=404, detail="No hay políticas almacenadas")
    response.headers["Content-Type"] = "application/ld+json"
    return data


@app.delete("/api/policy/{id}")
async def delete_policy(id: str):
    data = load_data()
    if id not in data:
        raise HTTPException(status_code=404, detail="Política no encontrada")

    policy_uri = f"http://example.com/policy:{id}"
    g.remove((policy_uri, None, None))

    del data[id]
    save_data(data, g)
    return {"message": "Política eliminada"}


@app.get("/api/policy/evaluate/{id}")
async def evaluate_policy_id(id: str, request: Request):
    query_params = request.query_params
    interpolations = {key: query_params.get(key) for key in query_params.keys()}

    try:
        key_function = interpolations.get("key")
        if key_function and key_function not in FUNCTIONS_MAP:
            raise HTTPException(status_code=400, detail="Función no válida para 'key'")

        selected_function = FUNCTIONS_MAP.get(key_function)
        interpolations["selected_function"] = selected_function

        if "face_uuid" not in interpolations:
            raise HTTPException(status_code=400, detail="Falta el parámetro 'face_uuid'")
        interpolations["face_uuid"] = interpolations.pop("face_uuid")

        data = load_data()
        print("Política cargada:", json.dumps(data["3331"], indent=4))

        policy = data.get(id)
        print("Face UUID recibido:", interpolations["face_uuid"])
        print("Face UUID en la política:", policy["permission"][0]["constraint"][0]["rightOperand"]["@value"])

        if not policy:
            raise HTTPException(status_code=404, detail="Política no encontrada")

        odre = ODRE()
        print("Evaluando política con ODRE...")

        evaluation_result = odre.enforce(policy=json.dumps(policy), interpolations=interpolations)

        if evaluation_result:
            document_url = policy["permission"][0]["target"]
            print(document_url)
            async with httpx.AsyncClient() as client:
                response = await client.get(document_url)
                if response.status_code == 200:
                    return Response(content=response.content, media_type="application/pdf")
                else:
                    raise HTTPException(status_code=500, detail="Error al obtener el documento")
        else:
            raise HTTPException(status_code=403, detail="Acceso denegado")

    except Exception as e:
        traceback.print_exc()
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
        save_data(data, g)

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
    if not key or not id:
        raise ValueError("Los parámetros 'key' e 'id' son obligatorios")

    if not os.path.exists(STATUS_FILE):
        raise FileNotFoundError(f"El archivo de estados '{STATUS_FILE}' no existe")

    try:
        with open(STATUS_FILE, "r") as file:
            statuses = json.load(file)

        policy_status = statuses.get(id)
        if not policy_status:
            return False

        current_value = policy_status.get(key)
        if current_value is None:
            raise ValueError(f"Clave '{key}' no encontrada en el estado de la política.")

        return current_value
    except Exception as e:
        raise RuntimeError(f"Error al verificar el estado: {str(e)}")


REGISTERED_UUIDS = {
    "cd42c43d-18c4-445f-b5a6-814bc29cb505": "User A",
    "f7bc80a8-a2bc-4fb3-9caf-4e65ebe3c89a": "User B",
    "7cc7a7ab-b4b0-49db-b251-1b2936efc287": "User C"
}


def face_recognition(face_uuid):
    print(f"Evaluando Face Recognition con UUID: {face_uuid}")
    return face_uuid in REGISTERED_UUIDS


FUNCTIONS_MAP = {
    "status_var": status_var,
    "face_recognition": face_recognition
}

# if __name__ == "_main_":
#     uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=False, log_level="debug", debug=True,
#                 workers=1, limit_concurrency=1, limit_max_requests=1)
