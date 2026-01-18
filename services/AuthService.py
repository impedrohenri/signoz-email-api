from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import os

API_USERNAME = os.getenv("API_USERNAME")
API_PASSWORD = os.getenv("API_PASSWORD")

security = HTTPBasic()

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    current_user_byte = credentials.username.encode("utf8")
    correct_user_byte = API_USERNAME.encode("utf8")
    
    current_pw_byte = credentials.password.encode("utf8")
    correct_pw_byte = API_PASSWORD.encode("utf8")
    
    is_correct_user = secrets.compare_digest(current_user_byte, correct_user_byte)
    is_correct_pw = secrets.compare_digest(current_pw_byte, correct_pw_byte)

    if not (is_correct_user and is_correct_pw):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
