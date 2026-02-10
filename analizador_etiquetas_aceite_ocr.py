#!/usr/bin/env python3
"""
Analizador de Etiquetas de Aceite - Versión con OCR
Extrae información sobre el origen del aceite de etiquetas en PDF
Usa OCR para PDFs con texto en imágenes
"""

import os
import re
import csv
from pathlib import Path
import pdfplumber
from PIL import Image
import pytesseract
import io
from typing import List, Tuple, Set

class AnalizadorEtiquetasAceiteOCR:
    """Analiza PDFs de etiquetas de aceite para extraer información de origen."""
    
    def __init__(self, carpeta_pdfs: str, archivo_salida: str = "origenes_aceite.csv"):
        """
        Inicializa el analizador.
        
        Args:
            carpeta_pdfs: Ruta a la carpeta con los PDFs
            archivo_salida: Nombre del archivo CSV de salida
        """
        self.carpeta_pdfs = Path(carpeta_pdfs)
        self.archivo_salida = archivo_salida
        
        # Patrones de búsqueda para detectar orígenes
        self.patrones_origen = [
            # Product of [País]
            r'Product\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            
            # Producto de [País]
            r'Producto\s+de\s+([A-ZÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÉÍÓÚÑ][a-záéíóúñ]+)?)',
            
            # Origen: [País/Países]
            r'Origen:\s*([A-ZÉÍÓÚÑa-záéíóúñ\s,y]+)',
            
            # Patrón específico para Kroger: I: ITALY, S: SPAIN, etc.
            r'([A-Z]+):\s+(ITALY|SPAIN|PORTUGAL|GREECE|MOROCCO|TURKEY|TUNISIA|CHILE|ARGENTINA|FRANCE)',
            
            # Countries identified in the date code: [lista de países]
            r'[Cc]ountries?\s+identified\s+in\s+the\s+date\s+code[:\s]+([A-Z\s,;:\.0-9]+)',
            
            # Aceite de oliva de [País]
            r'[Aa]ceite\s+(?:de\s+oliva\s+)?de\s+([A-ZÉÍÓÚÑ][a-záéíóúñ]+)',
            
            # Mezcla de aceites de [países]
            r'[Mm]ezcla\s+de\s+aceites?\s+de\s+(?:la\s+)?(?:Unión\s+Europea|UE|([A-ZÉÍÓÚÑa-záéíóúñ\s,y]+))',
            
            # Aceites de distintos orígenes / países
            r'[Aa]ceites?\s+de\s+(?:distintos\s+)?(?:orígenes?|países)\s*:?\s*([A-ZÉÍÓÚÑa-záéíóúñ\s,y]+)?',
            
            # Made in / Elaborado en / Distributed by
            r'(?:Made\s+in|Elaborado\s+en|Envasado\s+en|Product\s+of)\s+([A-ZÉÍÓÚÑ][a-záéíóúñ]+)',
            
            # Aceite de oliva virgen extra español
            r'[Aa]ceite\s+.*?\s+(español|española|italiano|italiana|griego|griega|tunecino|marroquí|portugués|portuguesa)',
            
            # UE / No UE
            r'(UE|Unión\s+Europea|No\s+UE|Fuera\s+de\s+la\s+UE|EU\s+Agriculture)',
            
            # Distributed by ... [país]
            r'Distributed\s+by.*?(?:in|from)\s+([A-Z][a-z]+)',
        ]
        
        # Normalización de países
        self.normalizacion_paises = {
            'spain': 'España',
            'españa': 'España',
            'español': 'España',
            'española': 'España',
            'italy': 'Italia',
            'italia': 'Italia',
            'italiano': 'Italia',
            'italiana': 'Italia',
            'greece': 'Grecia',
            'grecia': 'Grecia',
            'griego': 'Grecia',
            'griega': 'Grecia',
            'tunisia': 'Túnez',
            'túnez': 'Túnez',
            'tunecino': 'Túnez',
            'morocco': 'Marruecos',
            'marruecos': 'Marruecos',
            'marroquí': 'Marruecos',
            'portugal': 'Portugal',
            'portugués': 'Portugal',
            'portuguesa': 'Portugal',
            'turkey': 'Turquía',
            'turquía': 'Turquía',
            'turco': 'Turquía',
            'chile': 'Chile',
            'argentina': 'Argentina',
            'france': 'Francia',
            'francia': 'Francia',
            'ue': 'UE (Unión Europea)',
            'eu': 'UE (Unión Europea)',
            'unión europea': 'UE (Unión Europea)',
            'eu agriculture': 'UE (Unión Europea)',
            'no ue': 'No UE',
            'fuera de la ue': 'No UE',
        }
    
    def extraer_texto_pdf(self, ruta_pdf: Path) -> str:
        """
        Extrae el texto completo de un PDF usando extracción directa.
        
        Args:
            ruta_pdf: Ruta al archivo PDF
            
        Returns:
            Texto extraído del PDF
        """
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
        """
        Limpia el texto OCR corrigiendo errores comunes.
        
        Args:
            texto: Texto con posibles errores de OCR
            
        Returns:
            Texto corregido
        """
        # Corregir | seguido de : como I: (común en OCR)
        texto = re.sub(r'\|:', 'I:', texto)
        
        # Corregir l: como I: cuando está en contexto de códigos de país
        texto = re.sub(r'(?<= )l:', 'I:', texto)
        
        return texto
    
    def extraer_texto_ocr(self, ruta_pdf: Path) -> str:
        """
        Extrae texto usando OCR de las imágenes del PDF.
        
        Args:
            ruta_pdf: Ruta al archivo PDF
            
        Returns:
            Texto extraído por OCR
        """
        texto_ocr = ""
        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                for i, pagina in enumerate(pdf.pages):
                    # Convertir página a imagen
                    img = pagina.to_image(resolution=300)
                    pil_img = img.original
                    
                    # Aplicar OCR
                    texto = pytesseract.image_to_string(pil_img, lang='eng+spa')
                    if texto:
                        # Limpiar errores comunes de OCR
                        texto = self.limpiar_texto_ocr(texto)
                        texto_ocr += texto + "\n"
        except Exception as e:
            print(f"⚠️  Error OCR en {ruta_pdf.name}: {str(e)}")
        
        return texto_ocr
    
    def detectar_origenes(self, texto: str) -> Set[str]:
        """
        Detecta los países de origen mencionados en el texto.
        
        Args:
            texto: Texto extraído del PDF
            
        Returns:
            Conjunto de países detectados
        """
        origenes = set()
        
        # Lista de países válidos en inglés y español
        paises_validos = {
            'spain', 'españa', 'italy', 'italia', 'greece', 'grecia',
            'portugal', 'tunisia', 'túnez', 'morocco', 'marruecos',
            'turkey', 'turquía', 'chile', 'argentina', 'usa', 'eeuu',
            'france', 'francia', 'germany', 'alemania'
        }
        
        # Primero buscar el patrón específico de códigos de país (Kroger style)
        patron_codigos = r'([A-Z]+):\s+(ITALY|SPAIN|PORTUGAL|GREECE|MOROCCO|TURKEY|TUNISIA|CHILE|ARGENTINA|FRANCE)'
        matches_codigos = re.findall(patron_codigos, texto, re.IGNORECASE)
        for codigo, pais in matches_codigos:
            pais_limpio = pais.strip().lower()
            if pais_limpio in paises_validos or pais_limpio in self.normalizacion_paises:
                pais_normalizado = self.normalizacion_paises.get(pais_limpio, pais.strip().title())
                origenes.add(pais_normalizado)
        
        # Luego buscar otros patrones
        for patron in self.patrones_origen:
            matches = re.finditer(patron, texto, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Determinar qué grupo capturó el país
                grupo_pais = None
                if match.lastindex and match.lastindex >= 1:
                    # Buscar el primer grupo no vacío
                    for i in range(1, match.lastindex + 1):
                        if match.group(i) and match.group(i).strip():
                            grupo_pais = match.group(i)
                            break
                
                if grupo_pais:
                    # Limpiar y separar por comas, punto y coma o 'y'
                    paises_raw = re.split(r'[,;]|\sy\s|\sand\s', grupo_pais)
                    for pais in paises_raw:
                        # Quitar números y limpiar
                        pais_limpio = re.sub(r'\d+', '', pais).strip().lower()
                        
                        # Filtrar solo si es un país válido o está en normalización
                        if pais_limpio in paises_validos or pais_limpio in self.normalizacion_paises:
                            # Normalizar
                            pais_normalizado = self.normalizacion_paises.get(
                                pais_limpio, 
                                pais.strip().title()
                            )
                            if len(pais_normalizado) > 2:
                                origenes.add(pais_normalizado)
        
        return origenes
    
    def extraer_codigo_archivo(self, nombre_archivo: str) -> str:
        """
        Extrae el código de 6 cifras que empieza por 4 del nombre del archivo.
        
        Args:
            nombre_archivo: Nombre del archivo PDF
            
        Returns:
            Código extraído o nombre completo si no se encuentra el patrón
        """
        # Buscar patrón: 6 dígitos que empiezan por 4
        match = re.search(r'(4\d{5})', nombre_archivo)
        if match:
            return match.group(1)
        return nombre_archivo
    
    def procesar_carpeta(self) -> List[Tuple[str, str, str]]:
        """
        Procesa todos los PDFs de la carpeta.
        
        Returns:
            Lista de tuplas (nombre_archivo, código, orígenes)
        """
        if not self.carpeta_pdfs.exists():
            print(f"❌ La carpeta {self.carpeta_pdfs} no existe.")
            return []
        
        resultados = []
        archivos_pdf = list(self.carpeta_pdfs.glob("*.pdf")) + list(self.carpeta_pdfs.glob("*.PDF"))
        
        if not archivos_pdf:
            print(f"⚠️  No se encontraron archivos PDF en {self.carpeta_pdfs}")
            return []
        
        print(f"📂 Procesando {len(archivos_pdf)} archivos PDF...\n")
        
        for pdf_path in sorted(archivos_pdf):
            print(f"🔍 Analizando: {pdf_path.name}")
            
            # Extraer texto normal
            texto_normal = self.extraer_texto_pdf(pdf_path)
            
            # Extraer texto con OCR
            print(f"   → Aplicando OCR...")
            texto_ocr = self.extraer_texto_ocr(pdf_path)
            
            # Combinar ambos textos
            texto_completo = texto_normal + "\n" + texto_ocr
            
            # Detectar orígenes
            origenes = self.detectar_origenes(texto_completo)
            
            # Extraer código
            codigo = self.extraer_codigo_archivo(pdf_path.name)
            
            # Formatear orígenes
            origenes_str = ", ".join(sorted(origenes)) if origenes else "No detectado"
            
            print(f"   ✓ Código: {codigo}")
            print(f"   ✓ Orígenes: {origenes_str}\n")
            
            resultados.append((pdf_path.name, codigo, origenes_str))
        
        return resultados
    
    def generar_csv(self, resultados: List[Tuple[str, str, str]]):
        """
        Genera el archivo CSV con los resultados.
        
        Args:
            resultados: Lista de tuplas con los datos procesados
        """
        if not resultados:
            print("⚠️  No hay resultados para generar el CSV")
            return
        
        with open(self.archivo_salida, 'w', newline='', encoding='utf-8-sig') as archivo_csv:
            escritor = csv.writer(archivo_csv, delimiter=';')
            
            # Escribir encabezados
            escritor.writerow(['Nombre_Archivo', 'Código', 'Países_Origen'])
            
            # Escribir datos
            for fila in resultados:
                escritor.writerow(fila)
        
        print(f"✅ Archivo CSV generado: {self.archivo_salida}")
        print(f"📊 Total de etiquetas procesadas: {len(resultados)}")
    
    def ejecutar(self):
        """Ejecuta el proceso completo de análisis."""
        print("=" * 60)
        print("  ANALIZADOR DE ETIQUETAS DE ACEITE - ORIGEN (con OCR)")
        print("=" * 60)
        print()
        
        resultados = self.procesar_carpeta()
        self.generar_csv(resultados)
        
        print("\n" + "=" * 60)
        print("  PROCESO COMPLETADO")
        print("=" * 60)


def main():
    """Función principal."""
    # Configuración
    CARPETA_PDFS = "./etiquetas_pdf"  # Cambia esta ruta según necesites
    ARCHIVO_SALIDA = "origenes_aceite.csv"
    
    # Crear el analizador y ejecutar
    analizador = AnalizadorEtiquetasAceiteOCR(CARPETA_PDFS, ARCHIVO_SALIDA)
    analizador.ejecutar()


if __name__ == "__main__":
    main()
