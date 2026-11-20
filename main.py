import os
from pathlib import Path

# En Vercel solo /tmp es escribible: matplotlib guarda ahí su caché de fuentes
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
import matplotlib
matplotlib.use("Agg")  # backend sin pantalla, necesario en servidores
import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional, Literal
from fastapi.responses import HTMLResponse
from unidecode import unidecode
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

## Variables globales
BASE_DIR = Path(__file__).resolve().parent

polizas = pd.read_csv(BASE_DIR / "polizas_actuaria.csv")
app=FastAPI()
usuarios = {}  

## Pagina inicial

## CONEXION A GITHUB
import os
import base64
import requests


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_FILE = os.getenv("GITHUB_FILE")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")


def github_url():
    return (
        f"https://api.github.com/repos/"
        f"{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    )


def get_csv():
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    params = {
        "ref": GITHUB_BRANCH
    }

    response = requests.get(
        github_url(),
        headers=headers,
        params=params
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail="No fue posible obtener el CSV desde GitHub"
        )

    data = response.json()

    content = base64.b64decode(data["content"]).decode("utf-8")
    sha = data["sha"]

    return content, sha


def save_csv(content, sha):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    encoded_content = base64.b64encode(
        content.encode("utf-8")
    ).decode("utf-8")

    body = {
        "message": "Actualizar productos.csv desde la API",
        "content": encoded_content,
        "sha": sha,
        "branch": GITHUB_BRANCH
    }

    response = requests.put(
        github_url(),
        headers=headers,
        json=body
    )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=500,
            detail="No fue posible actualizar el CSV en GitHub"
        )

    return response.json()


def parse_csv(content):
    lines = content.strip().splitlines()

    headers = lines[0].split(",")

    rows = []

    for line in lines[1:]:
        values = line.split(",")

        row = dict(zip(headers, values))
        rows.append(row)

    return headers, rows


def build_csv(headers, rows):
    lines = [",".join(headers)]

    for row in rows:
        lines.append(
            ",".join(str(row[h]) for h in headers)
        )

    return "\n".join(lines) + "\n"



## API

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>FastAPI Dashboard</title>
            <style>
                body { font-family: sans-serif; background: #121212; color: white; padding: 2rem; text-align: center; }
                a { color: #4af; display: inline-block; margin: 10px; font-size: 1.2rem; }
            </style>
        </head>
        <body>
            <h1>API DE PROYECTO </h1>
            <a href="/docs"> Ir a Docs </a> 
        </body>
    </html>

    """

## 4: Crear modelos


class PolizaIn(BaseModel):
    cliente_id: int = Query(gt=0)
    edad: int = Query(ge=0, le=110)
    sexo: Literal["M", "F"]
    estado: str = Field(min_length=3)
    tipo_seguro: Literal["Vida", "Gastos Médicos", "Hogar", "Auto"]
    prima_anual: float = Field(gt=0)
    suma_asegurada: float = Field(gt=0)
    siniestros: int = Field(default=0, ge=0)
    ingreso_anual: Optional[float] = Field(default=None, ge=0)


class Poliza(PolizaIn):
    id: int


class PolizaPatch(BaseModel):
    cliente_id: Optional[int] = Query(default=None, gt=0)
    edad: Optional[int] = Query(default=None, ge=0, le=110)
    sexo: Optional[Literal["M", "F"]] = None
    estado: Optional[str] = Field(default=None, min_length=3)
    tipo_seguro: Optional[Literal["Vida", "Gastos Médicos", "Hogar", "Auto"]] = None
    prima_anual: Optional[float] = Field(default=None, gt=0)
    suma_asegurada: Optional[float] = Field(default=None, gt=0)
    siniestros: Optional[int] = Field(default=None, ge=0)
    ingreso_anual: Optional[float] = Field(default=None, ge=0)


class UsuarioIn(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)



import hashlib
def hash_password(password: str) -> str:
    return password
    



