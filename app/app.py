from fastapi import FastAPI, HTTPException, Body, Request, Response, Header
from fastapi.responses import JSONResponse
import secrets
from pydantic import BaseModel
from pyodre.odre import ODRE
import re
import httpx
import traceback
from fastapi.middleware.cors import CORSMiddleware
from app.services import *

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
from fastapi.openapi.utils import get_openapi

app = FastAPI()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="API de Políticas",
        version="1.0.0",
        description="API para gestionar políticas de privacidad",
        routes=app.routes,
    )

    # Configurar Swagger para aceptar application/ld+json en las peticiones
    for path in openapi_schema["paths"].values():
        for method in path:
            if "requestBody" in path[method]:
                path[method]["requestBody"]["content"] = {
                    "application/ld+json": path[method]["requestBody"]["content"]["application/json"]
                }
    for path in openapi_schema["paths"].values():
        for method in path:
            if "responses" in path[method]:
                for status_code in path[method]["responses"]:
                    content = path[method]["responses"][status_code].get("content")
                    if content and "application/json" in content:
                        content["application/ld+json"] = content.pop("application/json")

    app.openapi_schema = openapi_schema
    return app.openapi_schema



app.openapi = custom_openapi

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
        raise HTTPException(status_code=400, detail="The policy must have a 'uid' as an ID")
    if policy_uid in data:
        raise HTTPException(status_code=400, detail="ID already exists")
    data[policy_uid] = policy.odrl_policy
    save_data(data, g)
    response.headers["Content-Type"] = "application/ld+json"
    return policy


@app.get("/api/policy/{id}")
async def get_policy(id: str, response: Response, request: Request) :
    data = load_data()
    if id not in data:
        raise HTTPException(status_code=404, detail="Policy not found")
    response.headers["Content-Type"] = "application/ld+json"
    return data[id]


@app.get("/api/policy/")
async def get_policies(response: Response):
    data = load_data()
    if not data:
        raise HTTPException(status_code=404, detail="No stored policies found")
    response.headers["Content-Type"] = "application/ld+json"
    return data

@app.put("/api/policy/{id}")
async def update_policy(id: str, policy: Policy, response: Response):

    data = load_data()

    if id not in data:
        raise HTTPException(status_code=404, detail="Policy not found")

    del data[id]
    save_data(data, g)
    policy_uid = policy.odrl_policy.get("uid").split(":")[-1]
    if not policy_uid:
        raise HTTPException(status_code=400, detail="The policy must have a 'uid' as an ID")

    if policy_uid != id:
        raise HTTPException(status_code=400, detail="The 'uid' in the policy does not match the provided ID")

    data[policy_uid] = policy.odrl_policy
    save_data(data, g)

    response.headers["Content-Type"] = "application/ld+json"
    return {"message": "Policy successfully updated", "policy_id": policy_uid}


@app.delete("/api/policy/{id}")
async def delete_policy(id: str, response: Response):
    data = load_data()
    if id not in data:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy_uri = f"http://example.com/policy:{id}"
    g.remove((policy_uri, None, None))

    del data[id]
    save_data(data, g)
    response.headers["Content-Type"] = "application/ld+json"
    return {"message": "Policy successfully deleted", "id": id}

@app.get("/api/policy/evaluate/{id}")
async def evaluate_policy_id(id: str, request: Request):
    query_params = request.query_params
    interpolations = {key: query_params.get(key) for key in query_params.keys()}

    try:
        key_function = interpolations.get("key")
        if key_function and key_function not in FUNCTIONS_MAP:
            raise HTTPException(status_code=400, detail="Invalid function for 'key'")

        if FUNCTIONS_MAP.get(key_function):
            interpolations["selected_function"] = FUNCTIONS_MAP.get(key_function)

        if "face_uuid" in interpolations:
            interpolations["face_uuid"] = interpolations.pop("face_uuid")

        data = load_data()
        policy = data.get(id)
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        odre = ODRE()

        evaluation_result = odre.enforce(policy=json.dumps(policy), interpolations=interpolations)
        evaluation_log = {
            "parameters": dict(request.query_params),
            "evaluation_result": evaluation_result
        }
        save_evaluation_log(evaluation_log)
        if evaluation_result:
            document_url = policy["permission"][0]["target"]
            print(document_url)
            async with httpx.AsyncClient() as client:
                response = await client.get(document_url)
                if response.status_code == 200:
                    return Response(content=response.content, media_type="application/text")
                else:
                    raise HTTPException(status_code=500, detail="Error retrieving the document")
        else:
            raise HTTPException(status_code=403, detail="Denied access")

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/policy/evaluate")
async def evaluate_policy(policy: Policy, request: Request, response: Response):
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
        response.headers["Content-Type"] = "application/ld+json"
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

