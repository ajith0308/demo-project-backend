from fastapi import FastAPI
import models
from database import engine
from routers import auth
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:4200","https://your-render-domain.com", "https://onrender.com/", "https://mynexttcs.000webhostapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)

