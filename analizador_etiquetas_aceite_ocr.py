import os
import sys
import re
import csv
from pathlib import Path
import pdfplumber
from PIL import Image
import pytesseract
import io
from typing import List, Tuple, Set

class AnalizadorEtiquetasAceiteOCR:
    def __init__(self, carpeta_pdfs: str, archivo_salida: str = "origenes_aceite.csv"):
        self.carpeta_pdfs = Path(carpeta_pdfs)
        self.archivo_salida = archivo_salida
        
        # --- CONFIGURACIÓN CRÍTICA PARA EXE PORTÁTIL ---
        self.configurar_tesseract()
        
        # Patrones (sin cambios)
        self.patrones_origen = [
            r'Product\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'Producto\s+de\s+([A-ZÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÉÍÓÚÑ][a-záéíóúñ]+)?)',
            r'Origen:\s*([A-ZÉÍÓÚÑa-záéíóúñ\s,y]+)',
            r'([A-Z]+):\s+(ITALY|SPAIN|PORTUGAL|GREECE|MOROCCO|TURKEY|TUNISIA|CHILE|ARGENTINA|FRANCE)',
            r'[Cc]ountries?\s+identified\s+in\s+the\s+date\s+code[:\s]+([A-Z\s,;:\.0-9]+)',
            r'[Aa]ceite\s+(?:de\s+oliva\s+)?de\s+([A-ZÉÍÓÚÑ][a-záéíóúñ]+)',
            r'[Mm]ezcla\s+de\s+aceites?\s+de\s+(?:la\s+)?(?:Unión\s+Europea|UE|([A-ZÉÍÓÚÑa-záéíóúñ\s,y]+))',
            r'[Aa]ceites?\s+de\s+(?:distintos\s+)?(?:orígenes?|países)\s*:?\s*([A-ZÉÍÓÚÑa-záéíóúñ\s,y]+)?',
            r'(?:Made\s+in|Elaborado\s+en|Envasado\s+en|Product\s+of)\s+([A-ZÉÍÓÚÑ][a-záéíóúñ]+)',
            r'[Aa]ceite\s+.*?\s+(español|española|italiano|italiana|griego|griega|tunecino|marroquí|portugués|portuguesa)',
            r'(UE|Unión\s+Europea|No\s+UE|Fuera\s+de\s+la\s+UE|EU\s+Agriculture)',
            r'Distributed\s+by.*?(?:in|from)\s+([A-Z][a-z]+)',
        ]
        
        self.normalizacion_paises = {
            'spain': 'España', 'españa': 'España', 'español': 'España', 'española': 'España',
            'italy': 'Italia', 'italia': 'Italia', 'italiano': 'Italia', 'italiana': 'Italia',
            'greece': 'Grecia', 'grecia': 'Grecia', 'griego': 'Grecia', 'griega': 'Grecia',
            'tunisia': 'Túnez', 'túnez': 'Túnez', 'tunecino': 'Túnez',
            'morocco': 'Marruecos', 'marruecos': 'Marruecos', 'marroquí': 'Marruecos',
            'portugal': 'Portugal', 'portugués': 'Portugal', 'portuguesa': 'Portugal',
            'turkey': 'Turquía', 'turquía': 'Turquía', 'turco': 'Turquía',
            'chile': 'Chile', 'argentina': 'Argentina',
            'france': 'Francia', 'francia': 'Francia',
            'ue': 'UE (Unión Europea)', 'eu': 'UE (Unión Europea)',
            'unión europea': 'UE (Unión Europea)', 'eu agriculture': 'UE (Unión Europea)',
            'no ue': 'No UE', 'fuera de la ue': 'No UE',
        }

    def configurar_tesseract(self):
        """Magia para encontrar Tesseract dentro del EXE o en el sistema."""
        if getattr(sys, 'frozen', False):
            # Si es EXE, buscamos en la carpeta temporal _MEIPASS
            base_path = sys._MEIPASS
            tesseract_folder = os.path.join(base_path, 'Tesseract-OCR')
            exe_path = os.path.join(tesseract_folder, 'tesseract.exe')
            
            if os.path.exists(exe_path):
                pytesseract.pytesseract.tesseract_cmd = exe_path
                os.environ['TESSDATA_PREFIX'] = os.path.join(tesseract_folder, 'tessdata')
            else:
                print("⚠️ No encuentro Tesseract dentro del EXE.")
        else:
            # Si es script normal, confiamos en el PATH de Windows
            pass

    def extraer_texto_pdf(self, ruta_pdf: Path) -> str:
        texto_completo = ""
        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if texto:
                        texto_completo += texto + "\n"
        except Exception as e:
            print(f"⚠️  Error al leer {ruta_pdf.name}: {str(e)}")
        return texto_completo
    
    def limpiar_texto_ocr(self, texto: str) -> str:
        texto = re.sub(r'\|:', 'I:', texto)
        texto = re.sub(r'(?<= )l:', 'I:', texto)
        return texto
    
    def extraer_texto_ocr(self, ruta_pdf: Path) -> str:
        texto_ocr = ""
        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                for i, pagina in enumerate(pdf.pages):
                    img = pagina.to_image(resolution=300)
                    pil_img = img.original
                    # Intentamos usar español e inglés. Si falla, solo inglés por defecto
                    try:
                        texto = pytesseract.image_to_string(pil_img, lang='spa+eng')
                    except:
                        texto = pytesseract.image_to_string(pil_img)
                        
                    if texto:
                        texto = self.limpiar_texto_ocr(texto)
                        texto_ocr += texto + "\n"
        except Exception as e:
            print(f"⚠️  Error OCR en {ruta_pdf.name}: {str(e)}")
        return texto_ocr
    
    def detectar_origenes(self, texto: str) -> Set[str]:
        origenes = set()
        paises_validos = {
            'spain', 'españa', 'italy', 'italia', 'greece', 'grecia',
            'portugal', 'tunisia', 'túnez', 'morocco', 'marruecos',
            'turkey', 'turquía', 'chile', 'argentina', 'usa', 'eeuu',
            'france', 'francia', 'germany', 'alemania'
        }
        
        patron_codigos = r'([A-Z]+):\s+(ITALY|SPAIN|PORTUGAL|GREECE|MOROCCO|TURKEY|TUNISIA|CHILE|ARGENTINA|FRANCE)'
        matches_codigos = re.findall(patron_codigos, texto, re.IGNORECASE)
        for codigo, pais in matches_codigos:
            pais_limpio = pais.strip().lower()
            if pais_limpio in paises_validos or pais_limpio in self.normalizacion_paises:
                pais_normalizado = self.normalizacion_paises.get(pais_limpio, pais.strip().title())
                origenes.add(pais_normalizado)
        
        for patron in self.patrones_origen:
            matches = re.finditer(patron, texto, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                grupo_pais = None
                if match.lastindex and match.lastindex >= 1:
                    for i in range(1, match.lastindex + 1):
                        if match.group(i) and match.group(i).strip():
                            grupo_pais = match.group(i)
                            break
                
                if grupo_pais:
                    paises_raw = re.split(r'[,;]|\sy\s|\sand\s', grupo_pais)
                    for pais in paises_raw:
                        pais_limpio = re.sub(r'\d+', '', pais).strip().lower()
                        if pais_limpio in paises_validos or pais_limpio in self.normalizacion_paises:
                            pais_normalizado = self.normalizacion_paises.get(pais_limpio, pais.strip().title())
                            if len(pais_normalizado) > 2:
                                origenes.add(pais_normalizado)
        return origenes
    
    def extraer_codigo_archivo(self, nombre_archivo: str) -> str:
        match = re.search(r'(4\d{5})', nombre_archivo)
        if match:
            return match.group(1)
        return nombre_archivo
    
    def procesar_carpeta(self) -> List[Tuple[str, str, str]]:
        if not self.carpeta_pdfs.exists():
            return []
        
        resultados = []
        archivos_pdf = list(self.carpeta_pdfs.glob("*.pdf")) + list(self.carpeta_pdfs.glob("*.PDF"))
        
        print(f"📂 Procesando {len(archivos_pdf)} archivos PDF...\n")
        
        for pdf_path in sorted(archivos_pdf):
            print(f"🔍 Analizando: {pdf_path.name}")
            texto_normal = self.extraer_texto_pdf(pdf_path)
            texto_ocr = self.extraer_texto_ocr(pdf_path)
            texto_completo = texto_normal + "\n" + texto_ocr
            origenes = self.detectar_origenes(texto_completo)
            codigo = self.extraer_codigo_archivo(pdf_path.name)
            origenes_str = ", ".join(sorted(origenes)) if origenes else "No detectado"
            
            print(f"   ✓ Orígenes: {origenes_str}\n")
            resultados.append((pdf_path.name, codigo, origenes_str))
        
        return resultados
    
    def generar_csv(self, resultados: List[Tuple[str, str, str]]):
        if not resultados:
            print("⚠️  No hay resultados.")
            return
        
        with open(self.archivo_salida, 'w', newline='', encoding='utf-8-sig') as archivo_csv:
            escritor = csv.writer(archivo_csv, delimiter=';')
            escritor.writerow(['Nombre_Archivo', 'Código', 'Países_Origen'])
            for fila in resultados:
                escritor.writerow(fila)
        print(f"✅ CSV generado: {self.archivo_salida}")

    def ejecutar(self):
        print("=" * 60)
        print("  ANALIZADOR ACEITE OCR - PORTÁTIL")
        print("=" * 60)
        resultados = self.procesar_carpeta()
        self.generar_csv(resultados)
        print("\nPROCESO COMPLETADO")
        input("Presiona ENTER para salir...")

def main():
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    CARPETA_PDFS = os.path.join(application_path, "etiquetas_pdf")
    ARCHIVO_SALIDA = os.path.join(application_path, "origenes_aceite.csv")
    
    if not os.path.exists(CARPETA_PDFS):
        try:
            os.makedirs(CARPETA_PDFS)
            print(f"ℹ️  Carpeta creada: {CARPETA_PDFS}. Pon tus PDFs aquí.")
        except: pass

    analizador = AnalizadorEtiquetasAceiteOCR(CARPETA_PDFS, ARCHIVO_SALIDA)
    analizador.ejecutar()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
