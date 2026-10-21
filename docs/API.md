# API local de Ibiki Key

La API está apagada de forma predeterminada. Se activa en **Automatización** y solo escucha en `127.0.0.1`.

Usa este encabezado cuando exista un token:

```http
Authorization: Bearer TU_TOKEN
```

## Rutas

| Método | Ruta | Función |
|---|---|---|
| GET | `/health` | Estado básico |
| GET | `/v1/status` | Perfil, motores, perfiles y macros disponibles |
| GET | `/v1/variables` | Variables globales |
| POST | `/v1/profiles/{id}/activate` | Activa un perfil |
| POST | `/v1/macros/{id}/run` | Ejecuta una macro |
| POST | `/v1/variables/{nombre}` | Asigna `{"value": ...}` |

`/v1/status` incluye `automation_paused` y cada macro indica `scope` con valor `general` o `mouse`. Una solicitud para ejecutar una macro durante el pánico se acepta por HTTP, pero el motor la bloquea y registra el motivo.

Ejemplo PowerShell:

```powershell
$headers = @{ Authorization = "Bearer TU_TOKEN" }
Invoke-RestMethod http://127.0.0.1:8765/v1/status -Headers $headers
```

La Alpha no expone la API fuera del equipo y no incluye TLS. Para integraciones externas debe usarse un puente seguro y autenticado.
