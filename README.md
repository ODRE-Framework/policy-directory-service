# Police Directory API

Este proyecto es una API desarrollada con [FastAPI](https://fastapi.tiangolo.com/) para gestionar y consultar políticas de permisos utilizando un modelo RDF. Se enfoca en la creación, almacenamiento y consulta de políticas de acceso en formato ODRL.

## Características

- **EndPoint `/sparql`**: permite realizar consultas SPARQL a través de HTTP POST.
- **Almacenamiento**: utiliza `rdflib` para la creación y manipulación de políticas en formato RDF.
- **Formato**: soporta datos en `JSON-LD` y salida en `Turtle`.

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/ODRE-Framework/police-directory.git
   cd police-directory
   ```

2. Crea un entorno virtual y actívalo:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Uso

### Code deployment
1. Download the current git project
2. Navigate to the `./app` folder and run the following command:
   ```bash
   uvicorn app:app --reload
   ```
3. Una vez que el servidor esté en funcionamiento, puedes acceder a la documentación generada automáticamente por Swagger. Accede a la documentación de la API en [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Esta interfaz permite probar los endpoints y ver la documentación de la API. 

### Docker deployment

Copy the following receipe and run `docker-compose up` command:
```yml
services:
  policy-directory-service:
    image: acimmino/odre-pds:1.0.1
    ports:
      - "8000:8000"
```

## Ejemplo de Consulta SPARQL

Puedes enviar una consulta SPARQL usando una herramienta como `curl` o `Postman`:

```http
POST http://localhost:8000/sparql
Content-Type: application/json

{
  "query": "SELECT ?subject WHERE { ?subject ?predicate ?object }"
}
```

## Contribuciones


