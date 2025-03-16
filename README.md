# Serviço de Remoção de Senha de PDF

Este serviço permite remover senhas de arquivos PDF através de uma API REST.

## Requisitos

- Python 3.7+
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone este repositório
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Uso

Inicie o servidor:

```bash
python app.py
```

O servidor estará disponível em http://localhost:5000

### Endpoint

**POST /remove-pdf-password**

Remover a senha de um arquivo PDF.

**Corpo da requisição (JSON):**
```json
{
  "password": "senha_do_pdf",
  "pdf_base64": "base64_do_pdf_aqui"
}
```

**Resposta de sucesso:**
```json
{
  "pdf_base64": "base64_do_pdf_sem_senha"
}
```

**Resposta de erro:**
```json
{
  "error": "Descrição do erro"
}
```

## Possíveis erros

- "Senha incorreta": A senha fornecida não é válida para o PDF
- "O PDF não possui senha": O PDF fornecido não está protegido por senha
- "O arquivo base64 fornecido é inválido": O string fornecido não é um base64 válido
- "PDF em base64 não fornecido": Campo obrigatório não fornecido
- "Senha não fornecida": Campo obrigatório não fornecido
