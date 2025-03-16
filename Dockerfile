FROM python:3.9-slim

WORKDIR /app

# Copiar os arquivos de requisitos e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar os arquivos da aplicação
COPY . .

# Definir variáveis de ambiente
ENV PORT=8080
ENV MAX_PDF_SIZE_MB=3.0

# Expor a porta que o aplicativo usará
EXPOSE 8080

# Comando para iniciar o aplicativo
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
