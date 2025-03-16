from flask import Flask, request, jsonify
from flask_cors import CORS
from pdf_service import PDFService
import logging
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
logger = logging.getLogger('pdf_api')

app = Flask(__name__)
# Configuração do CORS - permite requisições apenas de class-one.com.br e seus subdomínios
CORS(app, resources={r"/*": {"origins": ["https://pdf.class-one.com.br",]}})

@app.route('/remove-pdf-password', methods=['POST'])
def remove_pdf_password():
    """
    Endpoint para remover senha de um PDF
    """
    try:
        # Verifica se os dados foram fornecidos corretamente
        data = request.json
        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400
            
        # Verifica tanto o formato camelCase quanto o snake_case para compatibilidade
        pdf_base64 = data.get('pdf_base64') or data.get('pdfBase64')
        password = data.get('password')
        
        if not pdf_base64:
            return jsonify({"error": "PDF em base64 não fornecido"}), 400
        if not password:
            return jsonify({"error": "Senha não fornecida"}), 400
        
        # Processa o PDF para remover a senha
        result_base64 = PDFService.remove_password(pdf_base64, password)
        
        # Retorna o PDF sem senha
        return jsonify({"pdf_base64": result_base64})
        
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
    # Usar variáveis de ambiente para porta e host, com valores padrão
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
