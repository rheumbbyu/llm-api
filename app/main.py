import logging 
import uuid #incident number 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm-api") #the internal logbook


from contextlib import asynccontextmanager #open for business! to closing 
from app.engine import EchoEngine, ml_models #your new machine 
from fastapi.middleware.cors import CORSMiddleware #like a reception desk 
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from pathlib import Path 

from fastapi import FastAPI, Request
from app.routers import generate, health
from app.schemas.response import APIError
from app.limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    # MORNING: turn on the machine 
    ml_models["engine"] = EchoEngine()
    print("Machine calibrated, Lab is open")
    yield #doors of the hospital are open!
    # EVENING: switch it off 
    ml_models.clear()
    print("Machine switched off, Lab is closed")

app = FastAPI(title="My LLM API", version="1.0", lifespan=lifespan)
app.state.limiter = limiter #sign in sheet or noticeboard
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) 
#over the limit --> polite 429 note 

app.add_middleware(
    CORSMiddleware, 
    allow_origin_regex=r"http://localhost(:\d+)?", #only localhost, any port. http://random-site.com will not be allowed
                                            #d+ means one or more digits; ? means optional
                                            #r means regex or regular expression 
    allow_methods=["GET", "POST"],  #approved request types
    allow_headers=["Content-Type"], #approved extra info on requests 
)

app.include_router(health.router)
app.include_router(generate.router)

@app.get("/")
def root(): 
    return {"message": "Hello, inference!"} #front door greeting of the hospital 

@app.exception_handler(Exception) 
async def unhandled_error(request: Request, exc: Exception):
    rid = str(uuid.uuid4()) #incident number 
    logger.error("Unhandled error, request_id: %s", rid, exc_info=exc) #full details to logbook 
    return JSONResponse(
        status_code=500,
        content=APIError(
            error="InternalServerError",
            code=500,
            request_id=rid,
            detail="An unexpected error occurred",
        ).model_dump(), #turns the note into plain data to send to user 
    )

# EXERCISE E FIRE DRILL 
# @app.get("/fire-drill") #TEMPORARY 
# def fire_drill():
#     raise RuntimeError("The centrifuge exploded")

@app.get("/demo", include_in_schema=False)  #the streaming demo page (hidden from /docs)
def demo():
    return FileResponse(Path(__file__).parent / "static" / "demo.html")
