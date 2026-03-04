# QF_Wiz Payload Fetch API

Local, stdlib-only HTTP service that returns Context Payload JSON by ticket id.

## Run

```powershell
$env:QF_WIZ_API_KEY = "set-a-secret"
python .\api\server.py
```

Default bind: `http://127.0.0.1:8787`

Optional overrides:
- `QF_WIZ_API_HOST`
- `QF_WIZ_API_PORT`

## Example

```powershell
$headers = @{ "X-API-Key" = $env:QF_WIZ_API_KEY }
Invoke-WebRequest -Uri http://127.0.0.1:8787/payload/T20260216.0014 -Headers $headers
```
