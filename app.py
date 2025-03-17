from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import sys
import traceback

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pdf_service.log')
    ]
)
logger = logging.getLogger('pdf_api')

logger.info("Iniciando serviço de PDF")

try:
    from pdf_service import PDFService
    logger.info("Módulo pdf_service importado com sucesso")
except ImportError as e:
    logger.critical(f"Erro ao importar módulo pdf_service: {str(e)}")
    sys.exit(1)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://pdf.class-one.com.br"}})

def get_status_html():
    return '''
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Status do Serviço | 📊</title>
        <link href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@0,200..1000;1,200..1000&display=swap" rel="stylesheet">
        <link rel="icon" type="image/png" href="https://i.ibb.co/MMdSHDp/financa.png">
        <style>
            html, body {
                margin: 0;
                padding: 0;
                height: 100%;
            }
            body {
                font-family: 'Nunito', sans-serif;
                background-color: #121212;
                color: #e0e0e0;
                padding: 20px;
                display: flex;
                justify-content: center;
                box-sizing: border-box;
            }
            .container {
                max-width: 800px;
                width: 100%;
                border-radius: 8px;
                height: max-content;
                padding: 20px;
                margin: auto 0;
            }
            h1 {
                color: #4caf50;
                text-align: center;
                margin-bottom: 30px;
                font-weight: 1000;
                margin-top: 0px;
                margin-bottom: 45px;
            }
            h2 {
                margin: 0;
            }
            .status-card {
                background-color: #2d2d2d;
                border-left: 4px solid #4caf50;
                padding: 30px 30px 30px 30px;
                border-radius: 4px;
                margin-bottom: 20px;
            }
            .status-card p {
                margin-bottom: 0px;
            }
            .endpoint-list {
                list-style-type: none;
                padding: 0;
                display: grid;
                gap: 15px;
            }
            .endpoint-item {
                background-color: #2d2d2d;
                padding: 20px 20px 20px 30px;
                border-radius: 4px;
                border-left: 4px solid #2196f3;
            }
            .endpoint-url {
                font-weight: bold;
                color: #2196f3;
            }
            .endpoint-p {
                margin-bottom: 0px;
            }
            .method {
                display: inline-block;
                padding: 3px 6px;
                background-color: #2196f3;
                color: white;
                border-radius: 3px;
                font-size: 0.8em;
                margin-right: 10px;
            }
            footer {
                text-align: center;
                margin-top: 30px;
                color: #757575;
                font-size: 0.9em;
            }
            footer p {
                margin: 0px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>STATUS DE SERVIÇO</h1>
            
            <div class="status-card">
                <h2>Status: <span style="color: #4caf50;">ONLINE</span></h2>
                <p>Os serviços disponíveis na API estão funcionando, conforme descritos abaixo.</p>
            </div>
            
            <ul class="endpoint-list">
                <li class="endpoint-item">
                    <span class="method">POST</span>
                    <span class="endpoint-url">/remove-pdf-password</span>
                    <p class="endpoint-p">Remove a senha de um arquivo PDF protegido.</p>
                </li>
                <li class="endpoint-item">
                    <span class="method">POST</span>
                    <span class="endpoint-url">/pdf-to-image</span>
                    <p class="endpoint-p">Converte um arquivo PDF para imagem.</p>
                </li>
            </ul>
            
            <footer>
                <p class="mb-0">Por Murilo Souza Ramos &copy; <span id="currentYear"></span></p>
            </footer>
        </div>
    <script>
        const currentYear = document.getElementById('currentYear');
        currentYear.textContent = new Date().getFullYear();
        
        function adjustHeight() {
            const windowHeight = window.innerHeight;
            document.documentElement.style.height = windowHeight + 'px';
            document.body.style.height = windowHeight + 'px';
            document.documentElement.style.setProperty('--real-height', windowHeight + 'px');
        }
        
        adjustHeight();
        window.addEventListener('DOMContentLoaded', adjustHeight);
        window.addEventListener('load', adjustHeight);
        window.addEventListener('resize', adjustHeight);
        
        setTimeout(adjustHeight, 100);
        setTimeout(adjustHeight, 500);
        setTimeout(adjustHeight, 1000);
    </script>
    </body>
    </html>
    '''

@app.before_request
def handle_requests():
    if request.method == 'GET' and 'text/html' in request.headers.get('Accept', ''):
        api_routes = ['/api/']
        if not any(request.path.startswith(route) for route in api_routes):
            return get_status_html()

@app.route('/remove-pdf-password', methods=['POST'])
def remove_pdf_password():
    try:
        logger.debug("Requisição recebida para remover senha de PDF")
        if not request.is_json:
            logger.warning("Requisição sem JSON válido")
            return jsonify({"error": "É necessário enviar dados em formato JSON"}), 400
            
        data = request.json
        if not data:
            logger.warning("JSON vazio recebido")
            return jsonify({"error": "Dados não fornecidos"}), 400
            
        pdf_base64 = data.get('pdf_base64') or data.get('pdfBase64')
        password = data.get('password')
        
        logger.debug(f"Dados recebidos: PDF fornecido: {bool(pdf_base64)}, Senha fornecida: {bool(password)}")
        
        if not pdf_base64:
            return jsonify({"error": "PDF em base64 não fornecido"}), 400
        if not password:
            return jsonify({"error": "Senha não fornecida"}), 400
        
        logger.debug("Tentando remover senha do PDF")
        result_base64 = PDFService.remove_password(pdf_base64, password)
        logger.info("Senha removida com sucesso")
        
        return jsonify({"pdf_base64": result_base64})
        
    except ValueError as e:
        logger.error(f"Erro de validação: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Erro interno: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

@app.route('/pdf-to-image', methods=['POST'])
def pdf_to_image():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
            
        pdf_base64 = data.get('pdf_base64') or data.get('pdfBase64')
        password = data.get('password')
        
        if not pdf_base64:
            return jsonify({"error": "PDF em base64 não fornecido"}), 400
        
        result_base64 = PDFService.pdf_to_image(pdf_base64, password)
        
        return jsonify({"image_base64": result_base64})
        
    except ValueError as e:
        logger.error(f"Erro de validação: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Erro interno: {str(e)}")
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

@app.route('/', methods=['GET'])
def health_check():
    if 'text/html' in request.headers.get('Accept', ''):
        return get_status_html()
    
    return jsonify({"status": "OK", "message": "Os serviços estão em funcionamento."})

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Iniciando servidor na porta {port}")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.critical(f"Erro ao iniciar o servidor: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
