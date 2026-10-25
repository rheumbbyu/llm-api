import json
import asyncio
import time 
import uuid #barcode or PIN generator 

from fastapi import APIRouter, HTTPException, Request 
from fastapi.responses import StreamingResponse
#HTTPException is how you send back a 400 "not found"  

from app.schemas.request import GenerateRequest
from app.schemas.response import GenerateResponse
from app.engine import ml_models #gives access to the equipment room 
from app.limiter import limiter 

#this brings the wing building tool and your intake form
router = APIRouter(prefix="/v1", tags=["inference"])
#this builds the laboratory wing on floor /v1. Every room here will start with /v1 (version number)
#if you edit this code you can open a floor called /v2 

_history: dict[str, GenerateResponse] = {}
#filing cabinet: barcode -> report 
#} is an empty cabinet to start with.
#dict[str, GenerateResponse] describes what's in it: the labels are text (barcodes), and the items are reports.
#The _ at the start is a convention meaning "this is for internal use in this file only."
#This cabinet lives in memory, so it's emptied whenever the server restarts. It's like a whiteboard, not a permanent records room. Real systems use a database
MAX_CONCURRENT = 2       #only 2 machines: at most 2 tests at once
INFERENCE_TIMEOUT = 10   #give up on a test after 10 seconds, 
                            #if you change it to 0.01 its milliseconds. the test took too long 
_sem = asyncio.Semaphore(MAX_CONCURRENT)  #the "machines in use" counter 
                #semaphore is the signout board for machines. each test has a spot and empties when it is done 


@router.post("/generate", response_model=GenerateResponse) 
@limiter.limit("5/minute") #each user: 5 samples per minute. can also use 10/hour, 100/day 
#POST or like submission of a sample, standard template 

# EXERCISE D VERSION 
# async def generate(request: GenerateRequest):
#     start = time.perf_counter()
#     #replaced: output = f"[ECHO]: {request.prompt}" #run the test, echoing the prompt back as a result. This is a stub, not a real llm
#     engine = ml_models["engine"]
#     result = await engine.generate(request.prompt, request.max_tokens, request.temperature)
#     output = result["text"]
    
#     elapsed_ms = (time.perf_counter() - start) * 1000 #milliseconds 

async def generate(req: GenerateRequest, request: Request):
    if _sem.locked():  #both machines busy? no free slots
        raise HTTPException(
            status_code=503,
            detail={"code": "SERVER_BUSY", "message": "All machines busy, try again shortly"},
            headers={"Retry-After": "5"}, #come back in 5 seconds
        )

    async with _sem:  #sign out a machine; it's returned automatically when done
        start = time.perf_counter()
        engine = ml_models["engine"]
        try:
            result = await asyncio.wait_for(
                engine.generate(req.prompt, req.max_tokens, req.temperature),
                timeout=INFERENCE_TIMEOUT,
            )
        except asyncio.TimeoutError:  #the test took too long
            raise HTTPException(
                status_code=504,
                detail={"code": "TIMEOUT", "message": "The test took too long"},
            )
        output = result["text"]
        elapsed_ms = (time.perf_counter() - start) * 1000
    
    prompt_tokens = len(req.prompt.split())
    completion_tokens = len(output.split())
    
    #return GenerateResponse(
    response = GenerateResponse( 
        request_id=str(uuid.uuid4()),
        generated_text=output,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        elapsed_ms=round(elapsed_ms, 2),
        #replaced model="stub"
        model = engine.name 
    )
    _history[response.request_id] = response #makes a copy under the barcode or PIN 
    return response 

@router.get("/generate/{request_id}", response_model=GenerateResponse) #GET BLUE 
def get_generation(request_id: str):
    if request_id not in _history: 
        raise HTTPException(
                status_code = 404, 
                detail={"code": "NOT_FOUND", "message": "No result with that barcode"},
        )
    return _history[request_id]


#STREAMING 
async def token_generator(prompt: str, max_tokens: int):
    words = f"[STREAM] {prompt}".split()        #the "results", one word each
    for word in words[:max_tokens]:              #stop once max_tokens 
        payload = json.dumps({"token": word + " "}) #writes the result as a json 
        yield f"data: {payload}\n\n"             #phone one result through
        await asyncio.sleep(0.2)                 #pretend the analyser takes 0.2s per result
    yield "data: [DONE]\n\n"                     #done, like the end 
    #a function that uses yield is a generator. like it prints everytime a result is done and not save it all up for a final result 

@router.post("/generate/stream")
async def generate_stream(req: GenerateRequest):
    return StreamingResponse(
        token_generator(req.prompt, req.max_tokens),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
