import os
import time
import uuid
import json
import logging
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from lambda_function import process_pdf_password_removal, CONFIG, logger

# Configuração do logger
logging.basicConfig(level=logging.INFO)

# Inicializar a aplicação Flask
app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas as rotas

@app.route('/', methods=['GET'])
def index():
    """Rota principal que redireciona para o site do projeto"""
    return redirect("https://pdf.class-one.com.br", code=302)

@app.route('/', methods=['POST'])
def remove_password():
    """Rota para processar a remoção de senha do PDF"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(json.dumps({
        'message': 'Requisição POST recebida',
        'request_id': request_id,
        'remote_addr': request.remote_addr,
    }))
    
    try:
        # Verificar se o conteúdo é JSON
        if not request.is_json:
            logger.warning(json.dumps({
                'message': 'Conteúdo não é JSON',
                'request_id': request_id,
                'content_type': request.content_type
            }))
            return jsonify({
                'error': 'FORMATO_INVÁLIDO', 
                'message': 'O conteúdo deve ser JSON'
            }), 400
            
        # Processar a remoção de senha
        result = process_pdf_password_removal(request.json, request_id, start_time)
        
        # Converter a resposta do formato Lambda para Flask
        status_code = result['statusCode']
        body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
        
        logger.info(json.dumps({
            'message': 'Requisição processada',
            'request_id': request_id,
            'status_code': status_code,
            'process_time_seconds': time.time() - start_time
        }))
        
        return jsonify(body), status_code
        
    except Exception as e:
        logger.error(json.dumps({
            'message': 'Erro ao processar requisição',
            'request_id': request_id,
            'error': str(e),
        }))
        return jsonify({
            'error': 'ERRO_INTERNO',
            'message': f'Erro interno do servidor: {str(e)}'
        }), 500

@app.route('/', methods=['OPTIONS'])
def handle_options():
    """Manipula requisições OPTIONS para CORS"""
    return '', 204

if __name__ == "__main__":
    # Obter a porta do ambiente (padrão do Koyeb) ou usar 5000 como padrão
    port = int(os.environ.get('PORT', 5000))
    
    # Configurar o tamanho máximo do PDF através de variável de ambiente
    max_pdf_size = os.environ.get('MAX_PDF_SIZE_MB')
    if max_pdf_size:
        CONFIG['MAX_PDF_SIZE_MB'] = float(max_pdf_size)
    
    logger.info(json.dumps({
        'message': 'Iniciando servidor Flask',
        'port': port,
        'max_pdf_size_mb': CONFIG['MAX_PDF_SIZE_MB']
    }))
    
    # Iniciar o servidor
    app.run(host='0.0.0.0', port=port)
