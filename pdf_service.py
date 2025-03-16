import base64
import pikepdf
import io
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
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
                raise ValueError("ERRO: O PDF não possui senha.")
            except pikepdf.PasswordError:
                # PDF requer senha, vamos tentar com a senha fornecida
                logger.info("PDF possui senha, tentando com a senha fornecida")
                input_stream.seek(0)  # Reset do ponteiro
            except Exception as e:
                logger.error(f"Erro ao verificar proteção do PDF: {e}")
                raise ValueError(f"ERRO: Não foi possível verificar a segurança do PDF.")
            
            # Agora tenta abrir com a senha
            try:
                pdf = pikepdf.open(input_stream, password=password)
                logger.info("PDF aberto com sucesso usando a senha fornecida.")
            except pikepdf.PasswordError as e:
                logger.error(f"Senha incorreta: {e}")
                raise ValueError("ERRO: A senha está errada")
            except Exception as e:
                logger.error(f"Erro ao abrir PDF com senha: {e}")
                raise ValueError(f"ERRO: ao abrir PDF com a senha informada.")
            
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

    @staticmethod
    def pdf_to_image(pdf_base64, password=None):
        """
        Converte um PDF em imagens.
        
        Args:
            pdf_base64 (str): PDF codificado em base64
            password (str, optional): Senha do PDF, se necessário
            
        Returns:
            dict: Um dicionário com o tipo do retorno ('image' ou 'zip') e o conteúdo em base64
            
        Raises:
            ValueError: Se ocorrer qualquer erro durante o processo
        """
        try:
            logger.info("Iniciando processo de conversão de PDF para imagem(ns)")
            
            # Decodificar o PDF de base64
            try:
                pdf_bytes = base64.b64decode(pdf_base64)
                logger.info("PDF decodificado com sucesso")
            except base64.binascii.Error as e:
                logger.error(f"Erro ao decodificar base64: {e}")
                raise ValueError("O arquivo base64 fornecido é inválido")
            
            # Usa PyMuPDF (fitz) para converter PDF para imagens
            import fitz  # PyMuPDF
            
            try:
                # Abrir o documento PDF
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
                
                # Verifica se há apenas uma página
                if len(pdf_document) == 1:
                    # Obtém a primeira página
                    page = pdf_document[0]
                    # Renderiza a página como imagem
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    
                    # Usando PIL como intermediário
                    from PIL import Image
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Salva a imagem como PNG em um buffer
                    image_buffer = io.BytesIO()
                    img.save(image_buffer, format="PNG")
                    image_buffer.seek(0)
                    
                    # Retorna a imagem em base64
                    image_base64 = base64.b64encode(image_buffer.getvalue()).decode('utf-8')
                    logger.info("PDF convertido para uma única imagem PNG com sucesso")
                    return {"type": "image", "content": image_base64}
                else:
                    # Cria um arquivo ZIP com todas as imagens
                    import zipfile
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zip_file:
                        for page_num in range(len(pdf_document)):
                            page = pdf_document[page_num]
                            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                            
                            img_buffer = io.BytesIO()
                            # Salva o pixmap como PNG no buffer
                            # Usando PIL como intermediário
                            from PIL import Image
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            img.save(img_buffer, format="PNG")
                            img_buffer.seek(0)
                            
                            # Adiciona a imagem ao ZIP
                            zip_file.writestr(f"pagina_{page_num+1}.png", img_buffer.getvalue())
                    
                    # Retorna o ZIP em base64
                    zip_buffer.seek(0)
                    zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
                    logger.info(f"PDF com {len(pdf_document)} páginas convertido para ZIP de imagens com sucesso")
                    return {"type": "zip", "content": zip_base64}
            finally:
                if 'pdf_document' in locals():
                    pdf_document.close()
                    
        except ValueError:
            # Re-lança ValueError para tratamento externo
            raise
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            raise ValueError(f"Erro ao processar o arquivo: {str(e)}")