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




