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
python run.py
```

Después abrí `http://127.0.0.1:5000` en el navegador.

La aplicación se crea mediante `create_app()` en `app/__init__.py`. La configuración de desarrollo y producción está en `config.py`. Flask-SQLAlchemy gestiona los modelos y crea las tablas que falten en `data/gastos.sqlite3`. La migración de gastos conserva sus registros y elimina la categoría anterior. Los Blueprints exponen las rutas y `app/services/pdf_service.py` procesa las facturas.

Los listados comienzan en el mes actual y permiten consultar meses anteriores con parámetros separados (`month=MM&year=YYYY` o el formato legado `month=YYYY-MM`) o rangos de fechas (`from`/`to`, inclusivos). El selector de mes filtra por mes y año; el rango filtra por fecha del movimiento. La importación PDF primero presenta una vista previa editable; solo se guarda después de confirmar. Al importar una tarjeta se indican por separado el mes de pago y el mes de resumen. Los totales Visa/Mastercard se agrupan por mes de pago y su detalle aparece al abrir cada tarjeta. Los reintegros se almacenan como importes positivos con tipo `refund` y se descuentan del gasto neto.

Las transferencias se interpretan como aportes para cubrir gastos, de acuerdo con el flujo existente. La brecha de cobertura se calcula como `50% del gasto neto - total transferido`; no representa el saldo disponible de cuentas bancarias.

La importacion de PDF funciona mejor con facturas que tengan texto seleccionable. Si el PDF es una imagen escaneada, primero habria que aplicarle OCR. Los gastos existentes sin tipo de tarjeta identificable se conservan como gastos manuales.

Antes de importar un PDF hay que seleccionar Visa o Mastercard e indicar el mes y año de pago y el mes y año correspondiente al resumen.

La pantalla inicial muestra dos modulos: `Gastos` y `Transferencias`. En transferencias se registra fecha, importe y destino, y se muestra la diferencia entre gastos del mes y transferencias del mes.
