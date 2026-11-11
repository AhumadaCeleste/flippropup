-- Flip PropUp · más tiempo para los cálculos pesados (por API el límite por defecto es de pocos segundos)
alter function recalcular_referencias() set statement_timeout = '180s';
alter function calcular_senales() set statement_timeout = '180s';
alter function registrar_mercado() set statement_timeout = '180s';
alter function marcar_salidas(text[], int) set statement_timeout = '120s';
alter function actualizar_publicaciones(jsonb) set statement_timeout = '120s';
