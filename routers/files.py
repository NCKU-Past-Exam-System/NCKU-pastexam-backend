from starlette.requests import Request
from fastapi import Depends, APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from dependencies.token import validate_token
from copy import copy
import os
from typing import Dict, Union, List

router = APIRouter(dependencies=[Depends(validate_token)])
authrouter = APIRouter()


def get_db(request: Request):
    connection = request.app.state.dbconn
    db = connection.cursor()
    try:
        yield db
    finally:
        db.close()
        connection.close()


@authrouter.get("/files/")
async def fetchfile(course_id: int = 0, file_name: str = ''):

    path = f"./static/{course_id}/{file_name}"

    if not os.path.exists(path):
        return {"status": "error", "message": "File or Directory do not exist."}
    if file_name == '' or course_id == 0:
        return {"status": "error", "message": "Please provide filename!"}
    return FileResponse(path=path)


@authrouter.post("/uploadfile/")
async def upload_file(file: UploadFile, year: int = 0, nickname: str = '', examtype: str = '', teacher: str = '', course_id: int = 0, db=Depends(get_db)):

    if (course_id > 48):
        return {"status": "error", "message": "Course do not exist!"}

    if course_id == 0 or examtype == '' or teacher == '' or year == 0:
        return {"status": "error", "message": "Please fill in every blank!"}
    if file == None:
        return {"status": "error", "message": "Please select a file!"}
    path = f"./static/{course_id}/{file.filename}"
    if os.path.exists(path):
        return {"status": "error", "message": "File already exist! Please rename file!"}

    content = file.file.read()
    fout = open(path, 'wb')
    fout.write(content)
    fout.close()
    query = "INSERT INTO files (course_id, teacher, year, type, filename, uploader) VALUES (%s, %s, %s, %s, %s, %s)"

    values = (course_id, teacher, year, examtype,
              file.filename, nickname)

    db.execute(query, values)

    db.commit()
    return {"status": "success", "message": f"Successfully uploaded {file.filename}"}
