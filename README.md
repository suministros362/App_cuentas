# App de carga de gastos

Aplicacion web simple en Python con Flask, frontend HTML/CSS/JS y base de datos SQLite.
Permite cargar gastos manuales, editar, eliminar, importar consumos desde facturas PDF de tarjeta Visa o Master, registrar transferencias y ver resumen mensual.

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecutar

```powershell
python app.py
```

Después abrí `http://127.0.0.1:5000` en el navegador.

La base de datos se crea automaticamente en `gastos.sqlite3` al iniciar la aplicacion.

La importacion de PDF funciona mejor con facturas que tengan texto seleccionable. Si el PDF es una imagen escaneada, primero habria que aplicarle OCR.

Antes de importar un PDF hay que seleccionar si el resumen corresponde a Visa o Master. Los gastos importados desde tarjeta guardan el mes en curso automaticamente.

La pantalla inicial muestra dos modulos: `Gastos` y `Transferencias`. En transferencias se registra fecha, importe y destino, y se muestra la diferencia entre gastos del mes y transferencias del mes.
