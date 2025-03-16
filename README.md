# Police Directory API

The **Police Directory API** is a FastAPI-based system for managing and querying **privacy policies** using an **RDF model**. It facilitates the creation, storage, and retrieval of access control policies based on the **ODRL** (Open Digital Rights Language) standard.

This API enables policy-based access control by evaluating user permissions before granting access to resources.

A [demo service](https://odrldirectory.linkeddata.es/) is available to test the API.

---

## **Features**
- **SPARQL Querying** (`/api/policy/sparql`): Perform SPARQL queries to retrieve policy information.
- **Policy Management** (`/api/policy/`): Supports **CRUD operations** to create, update, and delete policies.
- **Policy Evaluation** (`/api/policy/evaluate/{id}`): Evaluates policies based on interpolated parameters.
- **JSON-LD and Turtle Support**: Accepts **JSON-LD** input and stores policies in **Turtle** format.
- **Token-Based Authorization**: Secure API endpoints with authentication tokens.
- **Integration with RDF Graphs**: Uses `rdflib` for policy storage and querying.

---

## **Running with Docker**

### **1️⃣ Docker Compose Deployment**

Copy the following **`docker-compose.yml`** file and run:

```bash
docker-compose up

```

```yaml
version: '3.0'
services:
  directory:
    container_name: odre-pds
    image: acimmino/odre-pds:latest
    restart: unless-stopped
    ports:
      - "8000:8000"

```

### **2️⃣ Manual Docker Deployment**

1. **Build the Docker Image**:
    
    ```bash
    docker build -t police-directory-api .
    
    ```
    
2. **Run the Container**:
    
    ```bash
    docker run -p 8000:8000 police-directory-api
    
    ```
    

---

## **Installation**
### 1️⃣ **Clone the Repository**
```bash
git clone https://github.com/ODRE-Framework/police-directory.git
cd police-directory

```

### 2️⃣ **Create a Virtual Environment**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

```

### 3️⃣ **Install Dependencies**

```bash
pip install -r requirements.txt

```

### 4️⃣ **Configure the Application**

Modify `config.json` if needed before running the API:

```json
{
  "name": "fastapiproject",
  "version": "1.0.0",
  "debug": true
}

```

---

## **Running the API**

### **Locally (Development Mode)**

```bash
uvicorn app:app --reload --port 8000

```

By default, the API will be available at:

📌 [**http://127.0.0.1:8000/**](http://127.0.0.1:8000/)

---

## **Swagger API Documentation**

Once the server is running, you can access the **Swagger documentation** at:

📌 [**http://127.0.0.1:8000/docs**](http://127.0.0.1:8000/docs)

This interface allows you to **test the endpoints** and **view API documentation**.

---

## **API Endpoints**

### 🔹 **1. Policy Management**

| Method | Endpoint | Description |
| --- | --- | --- |
| **POST** | `/api/policy/` | Create a new policy |
| **GET** | `/api/policy/{id}` | Retrieve a specific policy by ID |
| **GET** | `/api/policy/` | Get all stored policies |
| **PUT** | `/api/policy/{id}` | Update an existing policy |
| **DELETE** | `/api/policy/{id}` | Delete a policy |

### 🔹 **2. Policy Evaluation**

| Method | Endpoint | Description |
| --- | --- | --- |
| **GET** | `/api/policy/evaluate/{id}` | Evaluate a policy based on parameters |
| **POST** | `/api/policy/evaluate` | Evaluate a given policy in JSON-LD format |

📌 **Example request for policy evaluation:**

```
GET http://localhost:8000/api/policy/evaluate/1234?key=face_recognition&face_uuid=abcd-efgh

```

### 🔹 **3. SPARQL Querying**

| Method | Endpoint | Description |
| --- | --- | --- |
| **POST** | `/api/policy/sparql` | Execute a SPARQL query on stored policies |

📌 **Example SPARQL request:**

```
POST http://localhost:8000/api/policy/sparql
Content-Type: application/json

{
  "query": "SELECT ?subject WHERE { ?subject ?predicate ?object }"
}

```

---



## **Contributions**

We welcome contributions! Please follow the standard GitHub workflow:

1. **Fork** the repository.
2. **Create** a new branch for your changes.
3. **Submit** a pull request with a detailed description.

---
