from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import sys
import traceback

# Configuração de logging mais detalhada
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pdf_service.log')
    ]
)
logger = logging.getLogger('pdf_api')

# Log de inicialização
logger.info("Iniciando serviço de PDF")

try:
    from pdf_service import PDFService
    logger.info("Módulo pdf_service importado com sucesso")
except ImportError as e:
    logger.critical(f"Erro ao importar módulo pdf_service: {str(e)}")
    sys.exit(1)

app = Flask(__name__)
# Configuração do CORS - permite requisições apenas de class-one.com.br e seus subdomínios
CORS(app, resources={r"/*": {"origins": "https://pdf.class-one.com.br"}})

@app.route('/remove-pdf-password', methods=['POST'])
def remove_pdf_password():
    """
    Endpoint para remover senha de um PDF
    """
    try:
        logger.debug("Requisição recebida para remover senha de PDF")
        # Verifica se os dados foram fornecidos corretamente
        if not request.is_json:
            logger.warning("Requisição sem JSON válido")
            return jsonify({"error": "É necessário enviar dados em formato JSON"}), 400
            
        data = request.json
        if not data:
            logger.warning("JSON vazio recebido")
            return jsonify({"error": "Dados não fornecidos"}), 400
            
        # Verifica tanto o formato camelCase quanto o snake_case para compatibilidade
        pdf_base64 = data.get('pdf_base64') or data.get('pdfBase64')
        password = data.get('password')
        
        logger.debug(f"Dados recebidos: PDF fornecido: {bool(pdf_base64)}, Senha fornecida: {bool(password)}")
        
        if not pdf_base64:
            return jsonify({"error": "PDF em base64 não fornecido"}), 400
        if not password:
            return jsonify({"error": "Senha não fornecida"}), 400
        
        # Processa o PDF para remover a senha
        logger.debug("Tentando remover senha do PDF")
        result_base64 = PDFService.remove_password(pdf_base64, password)
        logger.info("Senha removida com sucesso")
        
        # Retorna o PDF sem senha
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
    """
    Endpoint para converter PDF em imagem PNG
    """
    try:
        # Verifica se os dados foram fornecidos corretamente
        data = request.json
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
            
        # Verifica tanto o formato camelCase quanto o snake_case para compatibilidade
        pdf_base64 = data.get('pdf_base64') or data.get('pdfBase64')
        password = data.get('password')  # Senha é opcional
        
        if not pdf_base64:
            return jsonify({"error": "PDF em base64 não fornecido"}), 400
        
        # Processa o PDF para converter em PNG
        result_base64 = PDFService.pdf_to_image(pdf_base64, password)
        
        # Retorna a imagem PNG em base64
        return jsonify({"image_base64": result_base64})
        
    except ValueError as e:
        logger.error(f"Erro de validação: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Erro interno: {str(e)}")
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

@app.route('/', methods=['GET'])
def health_check():
    """
    Endpoint para verificação de saúde do servidor
    """
    return jsonify({"status": "ok", "message": "Serviço de remoção de senha de PDF está funcionando"})

if __name__ == '__main__':
    try:
        # Usar variáveis de ambiente para porta e host, com valores padrão
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Iniciando servidor na porta {port}")
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        logger.critical(f"Erro ao iniciar o servidor: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
