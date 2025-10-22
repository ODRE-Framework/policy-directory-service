from pydantic_settings import BaseSettings
import json
import os
DEFAULT_CONFIG = {
    "app_name": "policy-directory-service",
    "version": "1.0.0",
    "allowed_origins": ["*"],
    "data_file": "data/policies.json",
    "eval_log_file": "data/evaluations.json",
    "graph_file": "data/graph.ttl",
    "enable_config_endpoint": True,
    "description": "Default configuration for ODRE-PDS"
}

class Config(BaseSettings):
    app_name: str
    version: str
    allowed_origins: list[str]
    data_file: str
    eval_log_file: str
    graph_file: str
    enable_config_endpoint: bool = False

    class Config:
        env_file = ".env"
        extra = "allow"

def load_or_create_config() -> Config:
    config_path = "../data/config.json"

    if os.getenv("RESET_CONFIG", "false").lower() == "true" and os.path.exists(config_path):
        print("RESET_CONFIG flag detected — removing old configuration.")
        os.remove(config_path)
    if not os.path.exists(config_path):
        print("No configuration file found. Creating default config.json...")
        os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print("Default configuration created successfully.")
    else:
        print("Existing configuration file found. Loading...")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Config(**data)


app_config = load_or_create_config()
