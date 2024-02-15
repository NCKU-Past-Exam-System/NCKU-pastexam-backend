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
import time

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
    "https://nckucsie-pastexam-api.owenowenisme.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

def hasher(course_id:int,teacher:str,year:int,examtype:str,filename:str,username:str):
    hash_input = f"{course_id}_{teacher}_{year}_{examtype}_{username}_{filename}"
    return hashlib.sha256(hash_input.encode()).hexdigest()
def add_new_user(userinfo):
    db = get_db_connection()
    db_cursor = db.cursor()
    query = "INSERT INTO users (user_id, username) VALUES (%s, %s)"
    db_cursor.execute(query, (userinfo.get('email').split('@')[0], userinfo.get('given_name')))
    db.commit()
    return {"status":"success","message":"New user added!"}
@app.post("/token-verify/")
def token_verify(token: str = Cookie(None)):
    try: 
        userinfo=id_token.verify_oauth2_token(token, requests.Request(), clientId)
    except Exception as e:
        return {"status":"error","message":str(e)}
    db = get_db_connection()
    db_cursor = db.cursor()
    query = "SELECT * FROM users WHERE user_id = %s"
    db_cursor.execute(query, (userinfo.get('email').split('@')[0],))
    result = db_cursor.fetchone()
    if not result:
        add_new_user(userinfo)
    if(userinfo.get('hd') != 'gs.ncku.edu.tw'):
        return  {"status":"error","message":"Please use NCKU email to login!"}
    userinfo['status'] = 'success'
    return userinfo
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
async def fetch_file(request: Request,hash: str ='',token: str = Cookie(None)):

    if hash == '':
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Please fill in the hash!"}
        )
    
    userinfo=token_verify(token)
    if userinfo.get('status') == 'error':
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content = {"message":'Invalid token'}
        )

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
@app.post("/file/")
async def upload_file( request: Request,file:UploadFile ,year: int = 0, examtype : str = '', teacher : str = '', course_id:int=0 ,token: str = Cookie(None)):
    
    userinfo=token_verify(token)
    if userinfo.get('status') == 'error':
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content = {"message":'Invalid token'}
    )


    forlog= f"{userinfo.get('email')} {userinfo.get('given_name')}"
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s -"+forlog))
    logger.addHandler(handler)


    if course_id==0 or examtype == '' or teacher == '' or year == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Please fill in every blank!"}
        )
    if file == None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Please select a file!"}
        )
    
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
    original_filename = '.'.join(file.filename.split('.')[:-1])
    original_fileext = file.filename.split('.')[-1]
    while os.path.exists(path):
        file.filename = f"{original_filename}({i}).{original_fileext}"
        hashed_filename = hasher(course_id,teacher,year,examtype,file.filename,userinfo.get('given_name'))
        path = f"./static/{course_id}/{hashed_filename}"
        i += 1
            
    
    content = file.file.read()
    fout = open(path, 'wb')
    fout.write(content)
    fout.close()
    query = "INSERT INTO files (hash,course_id, teacher, year, type, name, uploader, upload_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    values = (hashed_filename,course_id, teacher, year, examtype, file.filename.split('_')[-1], userinfo.get('given_name'),int(time.time()))
    db_cursor.execute(query, values)
    query = "INSERT INTO uploader (hash,uploader_id) VALUES (%s, %s)"
    db_cursor.execute(query,(hashed_filename,userinfo.get('email').split('@')[0]))
    db.commit()
    return {"status":"success","message": f"Successfully uploaded {file.filename}"}
@app.delete("/file/")
async def delete_file(request: Request,hash: str ='',token: str = Cookie(None)):
    userinfo=token_verify(token)
    if userinfo.get('status') == 'error':
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content = {"message":'Invalid token'}
    )
    db = get_db_connection()
    db_cursor = db.cursor()
    query = "SELECT * FROM files WHERE hash = %s"
    db_cursor.execute(query, (hash,))
    result = db_cursor.fetchone()
    if result:
        course_id = result[1]
        query = "SELECT * FROM uploader WHERE hash = %s"
        db_cursor.execute(query, (hash,))
        uploader = db_cursor.fetchone()[1]
        if uploader != userinfo.get('email').split('@')[0]:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content = {"message":"You are not the uploader of this file!"}
            )
        
        path =f"./static/{course_id}/{hash}"
        if os.path.exists(path):
            os.remove(path)
        query = "DELETE FROM files WHERE hash = %s"
        db_cursor.execute(query, (hash,))
        query = "DELETE FROM uploader WHERE hash = %s"
        db_cursor.execute(query, (hash,))
        db.commit()
        return {"status":"success","message": f"Successfully deleted {result[6]}"}
    else:
        return {"status":"error","message": result}
@app.put("/file/")
async def update_file(request: Request,hash: str ='',year: int = 0, examtype : str = '', teacher : str = '',filename:str = '',token: str = Cookie(None)):
    userinfo=token_verify(token)
    if userinfo.get('status') == 'error':
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content = {"message":'Invalid token'}
    )
    if hash == '' or filename == '' or year == 0 or examtype == '' or teacher == '':
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Please fill the required arguments!"}
        )
    if examtype != 'quiz' and examtype != 'midterm' and examtype != 'final' and examtype != 'hw' and examtype != 'others':
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content = {"message":"Invalid examtype!"}
        )
    db = get_db_connection()
    db_cursor = db.cursor()
    query = "SELECT * FROM files WHERE hash = %s"
    db_cursor.execute(query, (hash,))
    result = db_cursor.fetchone()
    if result:
        if result[7] != userinfo.get('given_name'):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content = {"message":"You are not the uploader of this file!"}
            )
        if  examtype == '' or teacher == '' or year == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content = {"message":"Please fill in every blank!"}
            )
        query = "UPDATE files SET teacher = %s, year = %s, type = %s, name = %s WHERE hash = %s"
        db_cursor.execute(query, (teacher, year, examtype, filename,hash))
        db.commit()
        return {"status":"success","message": f"Successfully updated {result[6]}"}
    else:
        return {"status":"error","message": "File not found!"}
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
@app.get("/list-files-by-user/")
async def list_files_by_user(token: str = Cookie(None),db: cursor = Depends(get_db)):

    userinfo=token_verify(token)
    if userinfo.get('status') == 'error':
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content = {"message":"Invalid token"}
    )

    try:
        query = "SELECT * FROM files WHERE uploader = %s"
        db.execute(query, (userinfo.get('given_name'),))
        result = [dict((db.description[i][0], value) for i, value in enumerate(row)) for row in db.fetchall()]
        for i in result:
            query = "SELECT * FROM courses WHERE uid = %s"
            db.execute(query, (i['course_id'],))
            course = db.fetchone()
            i['course_name'] = course[4]
            i['sem']=course[3].split('-')[1]
        res = {}
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
@app.get("/latest-file/")
async def latest_file(request: Request,db: cursor = Depends(get_db),quantity:int =10):
    query = "SELECT hash,course_id,name,uploader,upload_time FROM files ORDER BY upload_time DESC LIMIT %s"
    db.execute(query, (quantity,))
    result = [dict((db.description[i][0], value) for i, value in enumerate(row)) for row in db.fetchall()]
    res = {}
    res["data"] = result

    for i in result:
        qurey = "SELECT * FROM courses WHERE uid = %s"
        db.execute(qurey, (i['course_id'],))
        course_info = db.fetchone()
        i['course_name'] = course_info[4]
        logger.info(course_info)
    
    if not result:
        res["status"] = "success"
        res["message"] = "No result found"
    else:
        res["status"] = "success"
    return res
