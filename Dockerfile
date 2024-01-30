FROM python:3.9 as requirements-stage

# 
WORKDIR /tmp

# 
RUN pip install poetry

# 
COPY ./pyproject.toml ./poetry.lock* /tmp/

# 
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# 
FROM python:3.9

# 
WORKDIR /app

# 
COPY --from=requirements-stage /tmp/requirements.txt /app/requirements.txt

# 
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY  . /app

# 
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7777"]