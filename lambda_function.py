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
    
    # Log do evento recebido para diagnóstico (removendo conteúdo binário grande)
    debug_event = event.copy() if isinstance(event, dict) else {'event_type': str(type(event))}
    if 'body' in debug_event and debug_event['body'] and len(debug_event['body']) > 200:
        debug_event['body'] = f"{debug_event['body'][:100]}... [truncado] ...{debug_event['body'][-100:]}"
    
    logger.info(json.dumps({
        'message': 'Evento recebido',
        'request_id': request_id,
        'event_keys': list(event.keys()) if isinstance(event, dict) else None,
        'debug_event': debug_event
    }))
    
    # Detecção mais robusta do método HTTP
    http_method = None
    
    if isinstance(event, dict):
        # Tentativa 1: Direto da propriedade httpMethod (API Gateway REST)
        http_method = event.get('httpMethod')
        
        # Tentativa 2: Do objeto requestContext (API Gateway HTTP API)
        if not http_method and 'requestContext' in event:
            request_context = event.get('requestContext', {})
            http_method = request_context.get('httpMethod') or request_context.get('http', {}).get('method')
        
        # Tentativa 3: Do objeto de método diretamente (invocação direta)
        if not http_method and 'method' in event:
            http_method = event.get('method')
            
        # Tentativa 4: Se há body mas não há método definido, assumir POST
        if not http_method and 'body' in event and event.get('body'):
            http_method = 'POST'
    
    logger.info(json.dumps({
        'message': 'Método HTTP detectado',
        'request_id': request_id,
        'http_method': http_method,
        'is_base64_encoded': event.get('isBase64Encoded', False) if isinstance(event, dict) else False
    }))
    
    try:
        # Direcionar para o handler adequado baseado no método HTTP
        if not http_method:
            return create_response(400, {'error': 'REQUISIÇÃO_INVÁLIDA', 'message': 'Não foi possível determinar o método HTTP'})
        elif http_method in ['GET', 'HEAD']:
            return handle_get_request(request_id)
        elif http_method == 'POST':
            return handle_post_request(event, request_id, start_time)
        elif http_method == 'OPTIONS':
            return handle_options_request(request_id)
        else:
            logger.warning(json.dumps({
                'message': 'Método HTTP inválido',
                'request_id': request_id,
                'http_method': http_method
            }))
            return create_response(400, {'error': 'MÉTODO_INVÁLIDO', 'message': 'Apenas métodos POST, GET e OPTIONS são suportados'})
    
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

def handle_get_request(request_id):
    """Manipula solicitações GET (redirecionamento)"""
    redirect_url = "https://pdf.class-one.com.br"
    logger.info(json.dumps({
        'message': 'Redirecionando solicitação GET',
        'request_id': request_id,
        'redirect_to': redirect_url
    }))
    return {
        'statusCode': 302,
        'headers': {
            'Location': redirect_url
        },
        'body': ''
    }

def handle_post_request(event, request_id, start_time):
    """Manipula solicitações POST (processamento de PDF)"""
    try:
        # Lidando com diferentes formas que o corpo pode chegar do API Gateway
        request_body = event.get('body', '{}')
        
        # Verificar se o corpo está codificado em base64 pelo API Gateway
        if isinstance(event, dict) and event.get('isBase64Encoded', False):
            logger.info(json.dumps({
                'message': 'Decodificando corpo Base64 do API Gateway',
                'request_id': request_id
            }))
            request_body = base64.b64decode(request_body).decode('utf-8')
        
        # Tentar fazer parse do JSON
        try:
            body = json.loads(request_body)
        except json.JSONDecodeError as e:
            logger.error(json.dumps({
                'message': 'Falha ao decodificar JSON do corpo',
                'request_id': request_id,
                'error': str(e),
                'body_preview': request_body[:100] if isinstance(request_body, str) else "Não é string"
            }))
            return create_response(400, {'error': 'JSON_INVÁLIDO', 'message': 'O corpo da requisição não contém um JSON válido'})
        
        return process_pdf_password_removal(body, request_id, start_time)
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(json.dumps({
            'message': 'Erro ao processar requisição POST',
            'request_id': request_id,
            'error': str(e),
            'traceback': error_details
        }))
        raise  # Propagar exceção para ser tratada pelo handler principal

def process_pdf_password_removal(body, request_id, start_time):
    """Processa a remoção de senha do PDF"""
    if 'pdfBase64' not in body:
        logger.warning(json.dumps({
            'message': 'Parâmetro pdfBase64 ausente',
            'request_id': request_id,
            'body_keys': list(body.keys())
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

def handle_options_request(request_id):
    """Manipula solicitações OPTIONS (para CORS)"""
    logger.info(json.dumps({
        'message': 'Respondendo solicitação OPTIONS',
        'request_id': request_id
    }))
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': CONFIG['CONTENT_TYPE'],
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Max-Age': '86400'
        },
        'body': '{}'
    }

def create_response(status_code, body):
    """Cria uma resposta com suporte a CORS."""
    headers = {
        'Content-Type': CONFIG['CONTENT_TYPE'],
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Max-Age': '86400'
    }
    
    return {
        'statusCode': status_code,
        'headers': headers,
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
