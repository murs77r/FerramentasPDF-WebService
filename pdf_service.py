import base64
import pikepdf
import io
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pdf_service')

class PDFService:
    @staticmethod
    def remove_password(pdf_base64, password):
        """
        Remove a senha de um PDF codificado em base64.
        
        Args:
            pdf_base64 (str): PDF codificado em base64
            password (str): Senha do PDF
            
        Returns:
            str: PDF sem senha codificado em base64
            
        Raises:
            ValueError: Se o PDF não tiver senha, a senha estiver incorreta ou ocorrer qualquer erro
        """
        try:
            logger.info("Iniciando processo de remoção de senha")
            
            # Decodificar o PDF de base64
            try:
                pdf_bytes = base64.b64decode(pdf_base64)
                logger.info("PDF decodificado com sucesso")
            except base64.binascii.Error as e:
                logger.error(f"Erro ao decodificar base64: {e}")
                raise ValueError("O arquivo base64 fornecido é inválido")
            
            # Cria buffer para o PDF
            input_stream = io.BytesIO(pdf_bytes)
            
            # Verifica se o PDF está protegido
            try:
                # Tenta abrir sem senha primeiro
                pdf_test = pikepdf.open(input_stream)
                pdf_test.close()
                logger.info("PDF não possui senha")
                raise ValueError("O PDF não possui senha")
            except pikepdf.PasswordError:
                # PDF requer senha, vamos tentar com a senha fornecida
                logger.info("PDF possui senha, tentando com a senha fornecida")
                input_stream.seek(0)  # Reset do ponteiro
            except Exception as e:
                logger.error(f"Erro ao verificar proteção do PDF: {e}")
                raise ValueError(f"Erro ao verificar proteção do PDF: {str(e)}")
            
            # Agora tenta abrir com a senha
            try:
                pdf = pikepdf.open(input_stream, password=password)
                logger.info("PDF aberto com sucesso usando a senha fornecida")
            except pikepdf.PasswordError as e:
                logger.error(f"Senha incorreta: {e}")
                raise ValueError("Senha incorreta")
            except Exception as e:
                logger.error(f"Erro ao abrir PDF com senha: {e}")
                raise ValueError(f"Erro ao abrir PDF com a senha: {str(e)}")
            
            # Salva o PDF sem senha
            output_stream = io.BytesIO()
            pdf.save(output_stream)
            output_stream.seek(0)
            logger.info("PDF salvo sem senha")
            
            # Codifica o resultado em base64
            result_base64 = base64.b64encode(output_stream.getvalue()).decode('utf-8')
            logger.info("PDF codificado em base64 com sucesso")
            
            return result_base64
            
        except ValueError:
            # Re-lança ValueError para tratamento externo
            raise
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise ValueError(f"Erro ao processar o arquivo: {str(e)}")
