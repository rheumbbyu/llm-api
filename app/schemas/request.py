from typing import Optional
from pydantic import BaseModel, Field, field_validator
#BaseModel is the blank form template
#Field is the rule for each box on the form 

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096, examples=["Once upon a time"])
    #... means required. the form is rejected if empty 
    #min_length and max_length are size limits example sample volume is between x and y
    max_tokens: int = Field(256, ge=1, le=2048)
    #ge=1 means greater than or equal to 1, le=2048 means less than or equal to 2048
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    #how creative the model is, 0.0 is strict, 2.0 is creative
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    seed: Optional[int] = None
    stream: bool = False
    #top_p is creativity setting; seed is the a batch number for reproducibility. use the same seed, you get the same result
    #stream is a yes/no box 
    
    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, v:str) -> str: #v is the value that was entered in the box
        v = v.strip() #removes whitespace from the beginning and end of the string 
        if not v:
            raise ValueError("Prompt cannot be empty or whitespace")
        return v
    
    