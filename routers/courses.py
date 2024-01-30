from starlette.requests import Request
from fastapi import Depends, APIRouter, HTTPException
from dependencies.token import validate_token
from copy import copy
from typing import Dict, Union, List

router = APIRouter()


def get_db(request: Request):
    connection = request.app.state.dbconn
    db = connection.cursor()
    try:
        yield db
    finally:
        db.close()
        connection.close()


@router.get("/main/{course_id:path}")
def list_all(course_id: str, db=Depends(get_db)):
    query = f"SELECT * FROM pastexam.files WHERE course_id = '{course_id}' ORDER BY year DESC;"
    db.execute(query)
    r = [dict((db.description[i][0], value)
              for i, value in enumerate(row)) for row in db.fetchall()]
    if r:
        return r
    else:
        return {"error": "not found"}


@router.get("/courselist")
async def get_courselist(
        db=Depends(get_db), key: str = 'none'):
    if key == 'none':
        query = "SELECT * FROM pastexam.courses;"
    else:
        query = f"SELECT * FROM pastexam.courses ORDER BY {key} , id ;"
    db.execute(query)
    r = [dict((db.description[i][0], value)
              for i, value in enumerate(row)) for row in db.fetchall()]
    if r:
        return r
    else:
        return {"error": "not found"}
