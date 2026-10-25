from typing import Optional
from pydantic import BaseModel

class GenerateResponse(BaseModel): #what goes out instead of what comes in
    request_id: str         #specimen barcode
    generated_text: str     #result of the test
    prompt_tokens: int      #how much sample came in
    completion_tokens: int  #how much result went out
    total_tokens: int       #total used, for billing
    elapsed_ms: float       #turnaround time in milliseconds
    model: str              #which machine ran the test

class APIError(BaseModel): #standard incident report 
    error: str              #what went wrong 
    code: int               #status code example 500
    request_id: str         #incident number to quote to IT service 
    detail: Optional[str]= None #optional message, something human
    