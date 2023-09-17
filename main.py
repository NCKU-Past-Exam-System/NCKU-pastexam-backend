import os
import json
from mysql.connector import cursor
from db import get_db, get_db_connection
from fastapi import FastAPI, Request, Depends, File, UploadFile, HTTPException, status, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Union
import logging
from google.auth import jwt, exceptions
from google.oauth2 import id_token
from google.auth.transport import requests




app = FastAPI(docs_url=None, redoc_url=None)
clientId = "761442466271-4e3pel8pnajc5lcv4c4psd1n83mb06os.apps.googleusercontent.com"

#logging
logger = logging.getLogger("uvicorn.access")
handler = logging.handlers.RotatingFileHandler("./api.log",mode="a",maxBytes = 10*1024*1024, backupCount = 3)

logging.basicConfig(level=logging.INFO)

origins = [
    "http://localhost:3000",
    "https://nckucsie-pastexam.owenowenisme.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/main/{course_id:path}")
def list_all(course_id:str ,db: cursor = Depends(get_db)):
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s -"))
    logger.addHandler(handler)
    query = f"SELECT * FROM pastexam.files WHERE course_id = '{course_id}' ORDER BY year DESC;"
    db.execute(query)
    r = [dict((db.description[i][0], value) for i, value in enumerate(row)) for row in db.fetchall()]
    if r:
        return r
    else:
        return {"error": "not found"}

@app.get("/courselist")
async def get_courselist(
                   db: cursor = Depends(get_db),key: str = 'none'):
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s -"))
    logger.addHandler(handler)
    if key == 'none':
        query = "SELECT * FROM pastexam.courses;"
    else :
         query = f"SELECT * FROM pastexam.courses ORDER BY {key} , id ;"
    db.execute(query)
    r = [dict((db.description[i][0], value) for i, value in enumerate(row)) for row in db.fetchall()]
    if r:
        return r
    else:
        return {"error": "not found"}

@app.get("/files/")
async def fetchfile(request: Request,course_id: int =0, file_name:str=''):
    
    path=f"./static/{course_id}/{file_name}"    

    oauth_jwt=request.headers.get('token')
    
    if(oauth_jwt == None):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Login first!"}
        )
    try: 
        userinfo=id_token.verify_oauth2_token(oauth_jwt, requests.Request(), clientId)
    except exceptions.InvalidValue as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Token Expired! Please Relogin!"}
        )
    except Exception as e:
        logging.info(e)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Unvalid Login! Please Relogin!"}
        )


    
    forlog= f"{userinfo.get('email')} {userinfo.get('given_name')}"
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s -"+forlog))
    logger.addHandler(handler)
    forlog=""
    if(userinfo.get('hd') != 'gs.ncku.edu.tw'):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Please use NCKU email to login!"}
        )
    if not os.path.exists(path) :
        return {"status":"error","message": "File or Directory do not exist."}
    if file_name == '' or course_id == 0:
        return {"status":"error","message": "Please provide filename!"}
    return FileResponse(path=path)

@app.post("/uploadfile/")
async def upload_file( request: Request, file:UploadFile ,year: int = 0, examtype : str = '', teacher : str = '', course_id:int=0 ,token: str=''):
    oauth_jwt=request.headers.get('token')
    
    if(oauth_jwt == None):
        return  {"status":"error","message":"Login first!"}


    try: 
        userinfo=id_token.verify_oauth2_token(oauth_jwt, requests.Request(), clientId)
    except exceptions.InvalidValue as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Token Expired! Please Relogin!"}
        )
    except Exception as e:
        logging.info(e)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Unvalid Login! Please Relogin!"}
        )

    if(course_id > 48):
        return  {"status":"error","message":"Course do not exist!"}

    forlog= f"{userinfo.get('email')} {userinfo.get('given_name')}"
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s -"+forlog))
    logger.addHandler(handler)

    if(userinfo.get('hd') != 'gs.ncku.edu.tw'):
        return  {"status":"error","message":"Please use NCKU email to login!"}
    if course_id==0 or examtype == '' or teacher == '' or year == 0:
        return {"status":"error","message": "Please fill in every blank!"}
    if file == None:
        return {"status":"error","message": "Please select a file!"}
    path = f"./static/{course_id}/{file.filename}"
    if os.path.exists(path) :
        return {"status":"error","message": "File already exist! Please rename file!"}
    content = file.file.read()
    fout = open(path, 'wb')
    fout.write(content)
    fout.close()
    db = get_db_connection()
    db_cursor = db.cursor()
    query = f"INSERT INTO `pastexam`.`files` (`course_id`, `teacher`, `year`, `type`, `filename`,`uploader`) VALUES ('{course_id}', '{teacher}', '{year}', '{examtype}', '{file.filename}','{userinfo.get('given_name')}');"
    db_cursor.execute(query)
    db.commit()
    return {"status":"success","message": f"Successfully uploaded {file.filename}"}


