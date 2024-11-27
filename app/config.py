import json
from pydantic import BaseSettings


class Config(BaseSettings):
    app_name: str
    version: str
    allowed_origins: list[str]
    data_file: str
    eval_log_file: str
    graph_file: str

    class Config:
        env_file = ".env"


with open("config.json") as file:
    json_config = json.load(file)

app_config = Config(**json_config)
