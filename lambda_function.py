import json
import base64
import traceback
import os
import tempfile
import time
import logging
import uuid
from contextlib import contextmanager
from pikepdf import Pdf, PasswordError

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurações carregadas de variáveis de ambiente
CONFIG = {
    'MAX_PDF_SIZE_MB': float(os.environ.get('MAX_PDF_SIZE_MB', '3.0')),
    'CORS_ORIGIN': os.environ.get('CORS_ORIGIN', '*'),
    'CONTENT_TYPE': 'application/json',
    'ALLOWED_METHODS': 'POST, OPTIONS'
}

@contextmanager
def safe_tempfile(suffix='.pdf'):
    """Gerenciador de contexto para criar e limpar arquivos temporários com segurança."""
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        yield temp_file.name
    finally:
        cleanup_temp_files(temp_file.name)

def lambda_handler(event, context):
    """
    AWS Lambda function para remover senha de documentos PDF.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(json.dumps({
        'message': 'Requisição recebida',
        'request_id': request_id,
        'http_method': event.get('httpMethod')
    }))
    
    try:
        # Verificar se método HTTP é POST
        if event.get('httpMethod') != 'POST':
            logger.warning(json.dumps({
                'message': 'Método HTTP inválido',
                'request_id': request_id,
                'http_method': event.get('httpMethod')
            }))
            return create_response(400, {'error': 'MÉTODO_INVÁLIDO', 'message': 'Apenas método POST é suportado'})
        
        # Processar corpo da requisição
        body = json.loads(event.get('body', '{}'))
        
        # Verificar se os parâmetros necessários foram fornecidos
        if 'pdfBase64' not in body:
            logger.warning(json.dumps({
                'message': 'Parâmetro pdfBase64 ausente',
                'request_id': request_id
            }))
            return create_response(400, {'error': 'PARÂMETRO_AUSENTE', 'message': 'O parâmetro pdfBase64 é obrigatório'})
        
        if 'password' not in body:
            logger.warning(json.dumps({
                'message': 'Parâmetro password ausente',
                'request_id': request_id
            }))
            return create_response(400, {'error': 'PARÂMETRO_AUSENTE', 'message': 'O parâmetro password é obrigatório'})
        
        # Decodificar o PDF de Base64
        try:
            pdf_data = base64.b64decode(body['pdfBase64'])
        except Exception as e:
            logger.error(json.dumps({
                'message': 'Falha ao decodificar PDF base64',
                'request_id': request_id,
                'error': str(e)
            }))
            return create_response(400, {'error': 'PDF_INVÁLIDO', 'message': 'O arquivo PDF enviado não é válido'})
        
        # Verificar o tamanho do PDF
        pdf_size_mb = len(pdf_data) / (1024 * 1024)  # Tamanho em MB
        logger.info(json.dumps({
            'message': 'Tamanho do PDF recebido',
            'request_id': request_id,
            'pdf_size_mb': pdf_size_mb
        }))
        
        if pdf_size_mb > CONFIG['MAX_PDF_SIZE_MB']:
            logger.warning(json.dumps({
                'message': 'Tamanho do PDF excedido',
                'request_id': request_id,
                'pdf_size_mb': pdf_size_mb,
                'limit_mb': CONFIG['MAX_PDF_SIZE_MB']
            }))
            return create_response(413, {'error': 'TAMANHO_EXCEDIDO', 
                                         'message': f'O tamanho do PDF ({pdf_size_mb:.2f}MB) excede o limite de {CONFIG["MAX_PDF_SIZE_MB"]}MB'})
        
        # Uso de gerenciadores de contexto para arquivos temporários
        with safe_tempfile() as temp_input_path, safe_tempfile() as temp_output_path:
            # Salvar PDF em arquivo temporário
            with open(temp_input_path, 'wb') as f:
                f.write(pdf_data)
            
            # Remover a senha do PDF
            try:
                with Pdf.open(temp_input_path, password=body['password']) as pdf:
                    # Se chegou até aqui, a senha estava correta
                    if not pdf.is_encrypted:
                        logger.info(json.dumps({
                            'message': 'PDF não está protegido por senha',
                            'request_id': request_id
                        }))
                        return create_response(400, {'error': 'PDF_SEM_SENHA', 'message': 'O PDF fornecido não está protegido por senha'})
                    
                    # Salvar PDF sem senha
                    logger.info(json.dumps({
                        'message': 'Removendo senha do PDF',
                        'request_id': request_id
                    }))
                    pdf.save(temp_output_path)
            except PasswordError:
                logger.warning(json.dumps({
                    'message': 'Senha incorreta fornecida',
                    'request_id': request_id
                }))
                return create_response(401, {'error': 'SENHA_INCORRETA', 'message': 'A senha fornecida está incorreta'})
            except Exception as e:
                error_details = traceback.format_exc()
                logger.error(json.dumps({
                    'message': 'Erro ao processar PDF',
                    'request_id': request_id,
                    'error': str(e),
                    'traceback': error_details
                }))
                return create_response(500, {
                    'error': 'ERRO_PROCESSAMENTO',
                    'message': f'Erro ao processar o arquivo PDF: {str(e)}',
                    'details': error_details
                })
            
            # Ler o PDF processado
            with open(temp_output_path, 'rb') as f:
                processed_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        process_time = time.time() - start_time
        logger.info(json.dumps({
            'message': 'Processamento concluído com sucesso',
            'request_id': request_id,
            'process_time_seconds': process_time
        }))
        
        # Retornar o PDF sem senha
        return create_response(200, {
            'message': 'Senha removida com sucesso',
            'pdfBase64': processed_pdf
        })
        
    except Exception as e:
        process_time = time.time() - start_time
        error_details = traceback.format_exc()
        logger.error(json.dumps({
            'message': 'Erro interno do servidor',
            'request_id': request_id,
            'error': str(e),
            'traceback': error_details,
            'process_time_seconds': process_time
        }))
        return create_response(500, {
            'error': 'ERRO_INTERNO',
            'message': f'Erro interno do servidor: {str(e)}',
            'details': error_details
        })

def create_response(status_code, body):
    """Cria uma resposta formatada para API Gateway."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': CONFIG['CONTENT_TYPE'],
            'Access-Control-Allow-Origin': CONFIG['CORS_ORIGIN'],
            'Access-Control-Allow-Methods': CONFIG['ALLOWED_METHODS'],
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body)
    }

def cleanup_temp_files(*file_paths):
    """Remove arquivos temporários."""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Arquivo temporário excluído: {path}")
        except OSError as e:
            # Loga o erro em vez de ignorar silenciosamente
            logger.warning(json.dumps({
                'message': 'Falha ao remover arquivo temporário',
                'file_path': path,
                'error': str(e)
            }))
