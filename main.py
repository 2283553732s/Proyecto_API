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

################ Funciones apoyo    ################################################################################

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


#######################################################################################################################################
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
    return hashlib.sha256(password).hexdigest()



## 5 Crear póliza
@app.post("/polizas", status_code=201)              
def crear_poliza(datos: PolizaIn):
    global polizas
    nuevo_id = max((polizas["id"])) + 1
    nueva = {"id": nuevo_id, **datos.model_dump()}
    print(nueva)
    for i in range(10):
        print()
    print("Aqui me quede")
    nuevo_df=pd.DataFrame([nueva])
    print(nuevo_df)

    polizas = pd.concat([polizas, nuevo_df], ignore_index=True)
    ## Intento de conectar:
    try:
        content, sha = get_csv()

        headers, rows = parse_csv(content)
        new_content = build_csv(headers, rows)

        save_csv(new_content, sha)
        

    except Exception:
        print("No se pudo guardar")
        return {"mensaje": "fallo al guardarse"}
    return {"mensaje": "Póliza creada correctamente", "poliza": polizas.to_dict()}        

    
##6 Reemplazar
@app.put("/polizas/{poliza_id}")
def reemplazar_poliza(poliza_id: int, datos: PolizaIn):
    if poliza_id not in polizas["id"].values:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")

    mask = polizas["id"] == poliza_id
    for columna, valor in datos.model_dump().items():
        polizas.loc[mask, columna] = valor

    fila_actualizada = polizas[mask].to_dict(orient="records")[0]

    ######## PENDIENTE 
    try:
        content, sha = get_csv()

        headers, rows = parse_csv(content)
        new_content = build_csv(headers, rows)

        save_csv(new_content, sha)
    except Exception:
        print("No se pudo guardar")

    return {"mensaje": "Póliza reemplazada", "poliza": fila_actualizada}

##7 Actualizar      #nooo
@app.patch("/polizas/{poliza_id}")
def modificar_poliza(poliza_id: int, cambios: PolizaPatch):
    if poliza_id not in polizas["id"].values:
        raise HTTPException(status_code=404, detail="Póliza no encontrada")

    datos_actualizados = cambios.model_dump(exclude_unset=True, exclude_none=True)

    mask = polizas["id"] == poliza_id
    for columna, valor in datos_actualizados.items():
        polizas.loc[mask, columna] = valor    
             
## porque es un dataframe, me costó mucho y me tuvo que ayudar un ser suprema por arriba de nuestro entendimiento con consciencia propia
    fila_actualizada = polizas[mask].to_dict(orient="records")[0]


    ######## PENDIENTE 
    try:
        content, sha = get_csv()

        headers, rows = parse_csv(content)
        new_content = build_csv(headers, rows)

        save_csv(new_content, sha)
    except Exception:
        print("No se pudo guardar")

###############################
    return {"mensaje": "Póliza actualizada", "poliza": fila_actualizada}

## 8 eliminar

@app.delete("/polizas/{poliza_id}")
def eliminar_poliza(poliza_id: int):
    p = buscar(poliza_id)  # si no existe, responde 404
    polizas.drop(index=poliza_id-1, inplace=True)
    return {"mensaje": f"Póliza {poliza_id} eliminada"}

    ######## PENDIENTE 
    try:
        content, sha = get_csv()

        headers, rows = parse_csv(content)
        new_content = build_csv(headers, rows)

        save_csv(new_content, sha)
    except Exception:
        print("No se pudo guardar")

###############################




