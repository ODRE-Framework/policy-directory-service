from fastapi import APIRouter, HTTPException, Body, Header
from app.config import app_config
import json

router = APIRouter()

@router.get("/", tags=["Setup"])
async def get_current_config():
    return app_config.dict()

@router.post("/", tags=["Setup"])
async def update_config(
    new_config: dict = Body(...),
    authorization: str = Header(None)
):
    # if authorization != "Bearer admin-secret":
    #     raise HTTPException(status_code=403, detail="Access denied")
    #
    try:
        for key, value in new_config.items():
            if hasattr(app_config, key):
                setattr(app_config, key, value)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown config key: {key}")

        with open("../data/config.json", "w") as f:
            json.dump(app_config.dict(), f, indent=4)

        return {"message": "Configuration updated successfully", "config": app_config.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
