import base64
import pikepdf
import io
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
logger = logging.getLogger('pdf_service')

class PDFService:
    @staticmethod
    def remove_password(pdf_base64, password):
        try:
            logger.info("Iniciando processo de remoção de senha")
            
            try:
                pdf_bytes = base64.b64decode(pdf_base64)
                logger.info("PDF decodificado com sucesso")
            except base64.binascii.Error as e:
                logger.error(f"Erro ao decodificar base64: {e}")
                raise ValueError("O arquivo base64 fornecido é inválido")
            
            input_stream = io.BytesIO(pdf_bytes)
            
            try:
                pdf_test = pikepdf.open(input_stream)
                pdf_test.close()
                logger.info("PDF não possui senha")
                raise ValueError("ERRO: O PDF não possui senha.")
            except pikepdf.PasswordError:
                logger.info("PDF possui senha, tentando com a senha fornecida")
                input_stream.seek(0)
            except Exception as e:
                logger.error(f"Erro ao verificar proteção do PDF: {e}")
                raise ValueError(f"ERRO: Não foi possível verificar a segurança do PDF.")
            
            try:
                pdf = pikepdf.open(input_stream, password=password)
                logger.info("PDF aberto com sucesso usando a senha fornecida.")
            except pikepdf.PasswordError as e:
                logger.error(f"Senha incorreta: {e}")
                raise ValueError("ERRO: A senha está errada")
            except Exception as e:
                logger.error(f"Erro ao abrir PDF com senha: {e}")
                raise ValueError(f"ERRO: ao abrir PDF com a senha informada.")
            
            output_stream = io.BytesIO()
            pdf.save(output_stream)
            output_stream.seek(0)
            logger.info("PDF salvo sem senha")
            
            result_base64 = base64.b64encode(output_stream.getvalue()).decode('utf-8')
            logger.info("PDF codificado em base64 com sucesso")
            
            return result_base64
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise ValueError(f"Erro ao processar o arquivo: {str(e)}")

    @staticmethod
    def pdf_to_image(pdf_base64, password=None):
        try:
            logger.info("Iniciando processo de conversão de PDF para imagem(ns)")
            
            try:
                pdf_bytes = base64.b64decode(pdf_base64)
                logger.info("PDF decodificado com sucesso")
            except base64.binascii.Error as e:
                logger.error(f"Erro ao decodificar base64: {e}")
                raise ValueError("O arquivo base64 fornecido é inválido")
            
            import fitz
            
            try:
                if password:
                    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                    if pdf_document.is_encrypted:
                        if not pdf_document.authenticate(password):
                            raise ValueError("Senha incorreta para o PDF")
                else:
                    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                    if pdf_document.is_encrypted:
                        raise ValueError("O PDF está protegido por senha. Forneça a senha correta.")
                
                logger.info(f"PDF aberto com sucesso. Número de páginas: {len(pdf_document)}")
                
                if len(pdf_document) == 1:
                    page = pdf_document[0]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    
                    from PIL import Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    image_buffer = io.BytesIO()
                    img.save(image_buffer, format="PNG")
                    image_buffer.seek(0)
                    
                    image_base64 = base64.b64encode(image_buffer.getvalue()).decode('utf-8')
                    logger.info("PDF convertido para uma única imagem PNG com sucesso")
                    return {"type": "image", "content": image_base64}
                else:
                    import zipfile
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zip_file:
                        for page_num in range(len(pdf_document)):
                            page = pdf_document[page_num]
                            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                            
                            img_buffer = io.BytesIO()
                            
                            from PIL import Image
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            img.save(img_buffer, format="PNG")
                            img_buffer.seek(0)
                            
                            zip_file.writestr(f"pagina_{page_num+1}.png", img_buffer.getvalue())
                    
                    zip_buffer.seek(0)
                    zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
                    logger.info(f"PDF com {len(pdf_document)} páginas convertido para ZIP de imagens com sucesso")
                    return {"type": "zip", "content": zip_base64}
            finally:
                if 'pdf_document' in locals():
                    pdf_document.close()
                    
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise ValueError(f"Erro ao processar o arquivo: {str(e)}")