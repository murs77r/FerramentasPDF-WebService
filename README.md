# 🔓 Removedor de Senha PDF com FLASK/PikePDF

Este repositório contém um serviço web para remoção de proteção por senha de arquivos PDF. O serviço recebe arquivos em formato Base64, remove a senha de proteção e retorna o PDF desbloqueado.

## ✨ Funcionalidades

- **Remoção de Senha:** Remove a proteção por senha de arquivos PDF
- **Conversão PDF para Imagem:** Converte arquivos PDF em imagens PNG
- **Interface API REST:** Permite integração fácil com outros sistemas
- **Segurança:** Suporta apenas requisições de domínios autorizados (CORS)
- **Verificação de Integridade:** Endpoint de health check para monitoramento

## 🔌 Endpoints da API

1. **Verificação de Saúde (Health Check)**
   - **URL:** `/`
   - **Método:** `GET`
   - **Resposta:** Status do serviço

2. **Remoção de Senha de PDF**
   - **URL:** `/remove-pdf-password`
   - **Método:** `POST`
   - **Corpo da Requisição:**
     ```json
     {
       "pdf_base64": "base64_encoded_pdf_string",
       "password": "pdf_password"
     }
     ```
   - **Resposta bem-sucedida:**
     ```json
     {
       "pdf_base64": "base64_encoded_unlocked_pdf_string"
     }
     ```

3. **Conversão de PDF para Imagem**
   - **URL:** `/pdf-to-image`
   - **Método:** `POST`
   - **Corpo da Requisição:**
     ```json
     {
       "pdf_base64": "base64_encoded_pdf_string",
       "password": "pdf_password"  // Opcional, necessário apenas se o PDF estiver protegido
     }
     ```
   - **Resposta bem-sucedida (PDF com uma página):**
     ```json
     {
       "type": "image",
       "content": "base64_encoded_image_string"
     }
     ```
   - **Resposta bem-sucedida (PDF com múltiplas páginas):**
     ```json
     {
       "type": "zip",
       "content": "base64_encoded_zip_file_containing_images"
     }
     ```

## 🛠️ Tecnologias Utilizadas

- **Python:** Linguagem de programação principal
- **Flask:** Framework web para criação da API
- **PikePDF:** Biblioteca para manipulação de PDFs
- **PyMuPDF:** Biblioteca para converter PDF em imagens
- **Pillow:** Biblioteca para processamento de imagens
- **Gunicorn:** Servidor WSGI para Python
- **Flask-CORS:** Gerenciamento de Cross-Origin Resource Sharing

## 🚀 Implantação

Este serviço está configurado para implantação na plataforma Koyeb, a partir das configurações atuais, mas funcionaria em qualquer ecossistema Function As A Service (FaaS).

## 📋 Requisitos

O arquivo `requirements.txt` tem a lista completa de dependências.

## 🚨 Limitações

- O serviço só pode remover senhas de PDFs quando a senha correta é fornecida
- Apenas PDFs com proteção por senha são processados
- PDFs muito grandes podem levar mais tempo para serem convertidos em imagens
