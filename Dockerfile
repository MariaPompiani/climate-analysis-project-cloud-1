# Use uma imagem Python base
FROM python:3.10-slim

# Defina o diretório de trabalho no contêiner
WORKDIR /app

# Copie o arquivo de dependências
COPY requirements.txt .

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copie o resto do código-fonte
# (Usamos .dockerignore para evitar copiar arquivos desnecessários)
COPY . .

# Comando padrão para executar o pipeline
CMD ["python", "src/run_pipeline.py"]