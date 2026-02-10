# Analizador de Etiquetas de Aceite - Origen

## Descripción
Scripts en Python para analizar etiquetas de productos de aceite en formato PDF y extraer información sobre el origen del aceite.

**Hay dos versiones disponibles:**
1. **analizador_etiquetas_aceite_basico.py** - Versión básica que solo extrae texto PDF
2. **analizador_etiquetas_aceite_ocr.py** - Versión avanzada con OCR (RECOMENDADA)

## Requisitos

### Instalación de dependencias

**Versión Básica:**
```bash
pip install pdfplumber
```

**Versión OCR (Recomendada):**
```bash
pip install pdfplumber pytesseract pillow
```

También necesitas instalar Tesseract OCR en tu sistema:
- **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng`
- **macOS:** `brew install tesseract`
- **Windows:** Descarga desde https://github.com/UB-Mannheim/tesseract/wiki

## Uso

### 1. Preparar los archivos

Coloca todos tus PDFs de etiquetas en una carpeta. Por defecto, el script busca en `./etiquetas_pdf/`

### 2. Ejecutar el script

**Versión OCR (Recomendada para etiquetas con imágenes):**
```bash
python analizador_etiquetas_aceite_ocr.py
```

**Versión Básica:**
```bash
python analizador_etiquetas_aceite_basico.py
```

### 3. Configuración personalizada

Puedes modificar las siguientes variables en la función `main()`:

```python
CARPETA_PDFS = "./etiquetas_pdf"  # Ruta a tu carpeta con PDFs
ARCHIVO_SALIDA = "origenes_aceite.csv"  # Nombre del archivo CSV de salida
```

## Resultado

El script genera un archivo CSV con las siguientes columnas:

- **Nombre_Archivo**: Nombre completo del archivo PDF
- **Código**: Código de 6 cifras que empieza por 4 (extraído del nombre del archivo)
- **Países_Origen**: Países de origen detectados en la etiqueta

### Ejemplo de salida CSV:

```
Nombre_Archivo;Código;Países_Origen
412345_aceite_virgen_extra.pdf;412345;España
423456_mezcla_europea.pdf;423456;UE (Unión Europea)
434567_blend_mediterraneo.pdf;434567;España, Grecia, Italia
```

## Patrones detectados

El script busca múltiples patrones para identificar el origen:

- ✅ "Producto de España"
- ✅ "Origen: Italia"
- ✅ "Aceite de oliva de Grecia"
- ✅ "Mezcla de aceites de la UE"
- ✅ "Aceites de distintos orígenes: España, Portugal"
- ✅ "Made in España"
- ✅ "Aceite español"
- ✅ "UE" / "No UE"

## Países reconocidos y normalizados

El script normaliza automáticamente variantes como:
- español/española → España
- italiano/italiana → Italia
- griego/griega → Grecia
- UE/Unión Europea → UE (Unión Europea)

## Notas importantes

1. **Nomenclatura de archivos**: El script funciona mejor si tus archivos siguen el patrón de 6 cifras empezando por 4 (ejemplo: `412345_descripcion.pdf`)

2. **Calidad del PDF**: Los resultados dependen de la calidad de extracción de texto del PDF. PDFs escaneados o con texto en imágenes pueden no ser procesados correctamente.

3. **CSV con punto y coma**: El CSV se genera usando `;` como delimitador para mejor compatibilidad con Excel en español.

4. **Codificación**: El archivo CSV se genera con codificación UTF-8 con BOM para correcta visualización de caracteres especiales en Excel.

## Solución de problemas

### El script no detecta orígenes

- Verifica que el PDF contenga texto extraíble (no solo imágenes)
- Revisa que el texto siga alguno de los patrones reconocidos
- Puedes agregar nuevos patrones en `self.patrones_origen`

### Error al leer PDFs

- Asegúrate de tener instalado PyPDF2: `pip install PyPDF2`
- Verifica que los archivos no estén corruptos
- Comprueba que tienes permisos de lectura en la carpeta

### No se encuentra la carpeta

- Verifica que la ruta en `CARPETA_PDFS` sea correcta
- Usa rutas absolutas si es necesario: `CARPETA_PDFS = "C:/Users/TuUsuario/Documentos/etiquetas_pdf"`

## Personalización

### Agregar nuevos patrones de búsqueda

Edita la lista `self.patrones_origen` en la clase `AnalizadorEtiquetasAceite`:

```python
self.patrones_origen = [
    # Tus patrones existentes...
    r'Tu\s+nuevo\s+patrón\s+([A-Z][a-z]+)',
]
```

### Agregar nuevos países

Edita el diccionario `self.normalizacion_paises`:

```python
self.normalizacion_paises = {
    'siria': 'Siria',
    'sirio': 'Siria',
    # ... más países
}
```

## Contacto y soporte

Para cualquier duda o mejora, revisa el código fuente y adapta según tus necesidades específicas.
