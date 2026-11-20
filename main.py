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
polizas=pd.read_csv("polizas_actuaria.csv")

app=FastAPI()
usuarios = {}  

## Pagina inicial

## CONEXION A GITHUB
import os
import base64
import requests

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


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

@app.get("/mostrar-polizas")
def mostrar_polizas ():
    return polizas.to_dict()

def buscar(poliza_id: int):
    for p in polizas["id"]:
        if p == poliza_id:
            return polizas[polizas["id"]==p].to_dict()
    raise HTTPException(status_code=404, detail="Póliza no encontrada")

@app.get("/buscar-poliza")
def buscar1(poliza_id: int):
    for p in polizas["id"]:
        if p == poliza_id:
            return polizas[polizas["id"]==p].to_dict()
    raise HTTPException(status_code=404, detail="Póliza no encontrada")

##
@app.get("/Filtrar-poliza")
def listar_polizas(estado: str = None, tipo_seguro: str = None,edad_min: int = None,edad_max: int = None):
    respuesta=polizas.copy()

    if estado is not None:
        respuesta=respuesta[respuesta["estado"]==estado]
    if tipo_seguro is not None:
        respuesta=respuesta[respuesta["tipo_seguro"]==tipo_seguro]
    if edad_min is not None:
        respuesta=respuesta[respuesta["edad"]>edad_min]
    if edad_max is not None:
        respuesta=respuesta[respuesta["edad"]<=edad_max]
    
    return respuesta.to_dict()


