# v0.4.2 — reparación del inicio en Windows

El error `CHECK constraint failed: kind IN ('Afiche','FotografÃa')` aparece cuando una versión anterior leyó los SQL UTF-8 con la codificación predeterminada de Windows. SQLite conserva esa restricción aunque se reemplace el SQL del proyecto.

## Actualizar sin borrar tus datos

1. Detén el servidor.
2. Copia los archivos de esta entrega sobre el proyecto, conservando `instance`, `.venv`, `.git` y tus respaldos. Como arreglo mínimo, reemplaza `app/community_data.py` y `app/__init__.py`.
3. Ejecuta `iniciar.bat` de nuevo. No ejecutes `init-db` ni borres `instance/depec.sqlite`.

El inicio detecta la restricción dañada antes de cargar la demo. Crea una copia SQLite consistente en `instance/depec.sqlite.pre-utf8-FECHA-HORA.bak` y reconstruye únicamente `media_files` en una transacción. Conserva sus identificadores, álbumes, vínculos, nombres de archivos, visibilidad, índices y disparadores; normaliza el tipo de fotografía. Las imágenes originales no se mueven ni se borran. Si falla la reparación, se revierte la reconstrucción y el respaldo permanece disponible. Una base correcta no se reconstruye ni genera este respaldo.

Todas las lecturas SQL del proyecto usan ahora `encoding='utf-8'`, incluidas inicialización, migraciones y generación de vistas previas. La corrección no requiere nuevas dependencias.

## Validación

Se reproduce el esquema mal codificado con variantes Windows-1252/Latin-1 y el texto del error reportado. Las pruebas verifican inicio con carga de demo, conservación de registros y credenciales, copia previa, integridad SQLite, índices y ausencia de duplicados al reiniciar. También comprueban el uso explícito de UTF-8 en instalaciones nuevas. Estas pruebas se ejecutan en Linux reproduciendo la base afectada; no equivalen a una ejecución nativa en Windows.
