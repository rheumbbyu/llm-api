#this is the admin wing

import time
from fastapi import APIRouter, HTTPException
from app.engine import ml_models

router = APIRouter(tags =["health"])
START_TIME = time.monotonic() #time is pythons clock, monotonic only moves forward. 
@router.get("/health")
def health():
    return {"status": "ok", "uptime_seconds": time.monotonic() - START_TIME}


#the sign at the door
@router.get("/info")
def info():
    return {"model": "stub", "version": "1.0", "max_tokens":1024}  
#admin door, stub means its a training mannequin,not a real llm
#1024 is the max number of tokens the model can handle, like a hospital lab's value/volume 

@router.get("/readiness")
def readiness():
    if "engine" not in ml_models:
        raise HTTPException(status_code=503, detail={"code": "NOT_READY", "message": "Machine still warming up"})
    return {"status": "ready"}
    
                                                