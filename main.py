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
import hashlib

# app = FastAPI(docs_url=None, redoc_url=None)
app = FastAPI()
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
def token_verify(token:str):
    try: 
        userinfo=id_token.verify_oauth2_token(token, requests.Request(), clientId)
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
    return userinfo
def hasher(course_id:int,teacher:str,year:int,examtype:str,filename:str,username:str):
    hash_input = f"{course_id}_{teacher}_{year}_{examtype}_{username}_{filename}"
    return hashlib.sha256(hash_input.encode()).hexdigest()
@app.get("/filelist/{course_id:path}")
def list_all(course_id:int ,db: cursor = Depends(get_db)):
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s -"))
    logger.addHandler(handler)
    try:
        query = "SELECT * FROM pastexam.files WHERE course_id = %s ORDER BY year DESC;"
        db.execute(query, (course_id,))
        result = [dict((db.description[i][0], value) for i, value in enumerate(row)) for row in db.fetchall()]
        res = {}
        logger.info(course_id)
        logger.info(result)
        res["data"] = result
        if not result:
            res["status"] = "success"
            res["message"] = "No result found"
        else:
            res["status"] = "success"
        return res
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/courselist")
async def get_courselist(db: cursor = Depends(get_db),key: str = 'none'):
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

@app.get("/file/")
async def fetchfile(request: Request,hash: str =''):
    
    if hash == '':
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Please fill in the hash!"}
        )
    # path=f"./static/{course_id}/{file_name}"

    # oauth_jwt=request.headers.get('token')
    
    # userinfo=token_verify(oauth_jwt)
    # forlog= f"{userinfo.get('email')} {userinfo.get('given_name')}"
    # handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s -"+forlog))
    # logger.addHandler(handler)
    # forlog=""
    # if(userinfo.get('hd') != 'gs.ncku.edu.tw'):
    #     return JSONResponse(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         content = {"message":"Please use NCKU email to login!"}
    #     )
    db = get_db_connection()
    db_cursor = db.cursor()
    query = "SELECT * FROM files WHERE hash = %s"
    db_cursor.execute(query, (hash,))
    result = db_cursor.fetchone()
    if result:
        course_id = result[1]
        path =f"./static/{course_id}/{hash}"
        return FileResponse(path=path)
    else:
        return result

@app.post("/uploadfile/")
async def upload_file( request: Request, file:UploadFile ,year: int = 0, examtype : str = '', teacher : str = '', course_id:int=0 ,token: str=''):
    oauth_jwt=request.headers.get('token')
    
    if(oauth_jwt == None):
        return  {"status":"error","message":"Login first!"}

    userinfo=token_verify(oauth_jwt)


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
    logger.info(path)
    # check if the course_id exist in the database
    db = get_db_connection()
    db_cursor = db.cursor()
    query = "SELECT * FROM courses WHERE uid = %s"
    db_cursor.execute(query, (course_id,))
    
    if not db_cursor.fetchone():
        return {"status":"error","message": "Course not found!"}
    
    if not os.path.exists(f"./static/{course_id}"):
        os.makedirs(f"./static/{course_id}")
    
    # get the filename expect the extension
    
    hashed_filename = hasher(course_id,teacher,year,examtype,file.filename,userinfo.get('given_name'))
    path = f"./static/{course_id}/{hashed_filename}"
    i=1
    while os.path.exists(path):
        file.filename = f"{'.'.join(file.filename.split('(')[:-1])}({i}).{file.filename.split('.')[-1]}"
        hashed_filename = hasher(course_id,teacher,year,examtype,file.filename,userinfo.get('given_name'))
        path = f"./static/{course_id}/{hashed_filename}"
        i += 1
            
    
    content = file.file.read()
    fout = open(path, 'wb')
    fout.write(content)
    fout.close()
    query = "INSERT INTO files (hash,course_id, teacher, year, type, name, uploader) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    values = (hashed_filename,course_id, teacher, year, examtype, file.filename.split('_')[-1], userinfo.get('given_name'))

    db_cursor.execute(query, values)
    db.commit()
    return {"status":"success","message": f"Successfully uploaded {file.filename}"}
@app.get("/search/")
async def search(request: Request, db: cursor = Depends(get_db),uid:int=0 ,course_name: str = '', dept: str = '', instructor: str = ''):
    query = "SELECT * FROM courses WHERE "
    conditions = []
    parameters = []
    if uid>0:
        conditions.append("uid = %s")
        parameters.append(uid)
    if course_name:
        conditions.append("name LIKE %s")
        parameters.append(f"%{course_name}%")
    if dept:
        conditions.append("dept = %s")
        parameters.append(dept)
    if instructor:
        conditions.append("teacher LIKE %s")
        parameters.append(f"%{instructor}%")

    if conditions:
        query += " AND ".join(conditions)
    else:
        return {"status": "error", "message": "Please fill in at least one blank!"}

    logger.info(query)
    try:
        db.execute(query, parameters)
        rows = db.fetchall()
        columns = [col[0] for col in db.description]  # Getting column names from the cursor
        results = [dict(zip(columns, row)) for row in rows]  # Constructing a dict for each row
        res = {}
        res["data"] = results
        if not results:
            res["status"] = "success"
            res["message"] = "No result found"
        else:
            res["status"] = "success"
        return res  # This will be automatically converted to JSON by FastAPI
    except Exception as e:
        return {"status": "error", "message": str(e)}

