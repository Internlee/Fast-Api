from pydantic import BaseModel

class Job(BaseModel):
    company:str
    title:str
    redirectLink:str
    qualifications: list[str]
    location : str
    duration: str
    basedJob:str
    experience:str
    stipend:str = "check source site"

