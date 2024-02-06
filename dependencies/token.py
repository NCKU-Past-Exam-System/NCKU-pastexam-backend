from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request
import datetime
import requests
import os
from fastapi.responses import JSONResponse
from google.auth import jwt, exceptions
from google.oauth2 import id_token
from google.auth.transport import requests

clientId = os.getenv("clientId", os.urandom(24))


def validate_token(token: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    if (token == None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Login first!",
        )
    try:
        userinfo = id_token.verify_oauth2_token(
            token, requests.Request(), clientId)
    except exceptions.InvalidValue as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token Expired! Please Relogin!",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unvalid Login! Please Relogin!",
        )

    if (userinfo.get('hd') != 'gs.ncku.edu.tw'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please use NCKU email to login!",
        )

    return token
