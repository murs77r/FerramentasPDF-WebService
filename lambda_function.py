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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CONFIG = {
    'MAX_PDF_SIZE_MB': float(os.environ.get('MAX_PDF_SIZE_MB', '3.0')),
    'CONTENT_TYPE': 'application/json'
}

@contextmanager
def safe_tempfile(suffix='.pdf'):
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        yield temp_file.name
    finally:
        cleanup_temp_files(temp_file.name)

def lambda_handler(event, context):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(json.dumps({
        'message': 'Requisição recebida',
        'request_id': request_id,
        'http_method': event.get('httpMethod')
    }))
    
    try:
        if event.get('httpMethod') != 'POST':
            logger.warning(json.dumps({
                'message': 'Método HTTP inválido',
                'request_id': request_id,
                'http_method': event.get('httpMethod')
            }))
            return create_response(400, {'error': 'MÉTODO_INVÁLIDO', 'message': 'Apenas método POST é suportado'})
        
        body = json.loads(event.get('body', '{}'))
        
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
        
        try:
            pdf_data = base64.b64decode(body['pdfBase64'])
        except Exception as e:
            logger.error(json.dumps({
                'message': 'Falha ao decodificar PDF base64',
                'request_id': request_id,
                'error': str(e)
            }))
            return create_response(400, {'error': 'PDF_INVÁLIDO', 'message': 'O arquivo PDF enviado não é válido'})
        
        pdf_size_mb = len(pdf_data) / (1024 * 1024)
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
        
        with safe_tempfile() as temp_input_path, safe_tempfile() as temp_output_path:
            with open(temp_input_path, 'wb') as f:
                f.write(pdf_data)
            
            try:
                with Pdf.open(temp_input_path, password=body['password']) as pdf:
                    if not pdf.is_encrypted:
                        logger.info(json.dumps({
                            'message': 'PDF não está protegido por senha',
                            'request_id': request_id
                        }))
                        return create_response(400, {'error': 'PDF_SEM_SENHA', 'message': 'O PDF fornecido não está protegido por senha'})
                    
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
            
            with open(temp_output_path, 'rb') as f:
                processed_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        process_time = time.time() - start_time
        logger.info(json.dumps({
            'message': 'Processamento concluído com sucesso',
            'request_id': request_id,
            'process_time_seconds': process_time
        }))
        
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
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': CONFIG['CONTENT_TYPE'],
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body)
    }

def cleanup_temp_files(*file_paths):
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Arquivo temporário excluído: {path}")
        except OSError as e:
            logger.warning(json.dumps({
                'message': 'Falha ao remover arquivo temporário',
                'file_path': path,
                'error': str(e)
            }))
