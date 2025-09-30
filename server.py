import os
from pathlib import Path

from flask import Flask, request, Response
import requests


app = Flask(__name__)


def _sitekey() -> str:
    # 1) keys/hcaptcha (если есть)
    key_path = Path("keys/hcaptcha")
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()
    # 2) env
    env_val = os.getenv("HCAPTCHA_SITEKEY")
    if env_val:
        return env_val
    # 3) тестовый ключ
    return "4434d6ba-bccc-481c-8f4a-e806b41a6b10"


def _secret() -> str:
    # 1) keys/hcaptcha.secret или keys/hcaptcha_secret (любой из них)
    for name in ("keys/hcaptcha.secret", "keys/hcaptcha_secret"):
        p = Path(name)
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    # 2) env
    env_val = os.getenv("HCAPTCHA_SECRET")
    if env_val:
        return env_val
    # 3) тестовый секрет
    return "0x0000000000000000000000000000000000000000"


def _page_html() -> str:
    key = _sitekey()
    return f"""<!doctype html>
<html lang=\"ru\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>hCaptcha Demo (легальная интеграция)</title>
  <script src=\"https://js.hcaptcha.com/1/api.js\" async defer></script>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 24px; }}
    .card {{ max-width: 520px; margin: 0 auto; padding: 24px; border: 1px solid #e3e3e3; border-radius: 12px; }}
    button {{ padding: 10px 16px; border-radius: 8px; border: 1px solid #444; background: #111; color: #fff; cursor: pointer; }}
    button:disabled {{ opacity: 0.6; cursor: not-allowed; }}
    .result {{ margin-top: 16px; white-space: pre-wrap; }}
  </style>
  <meta http-equiv=\"Content-Security-Policy\" content=\"upgrade-insecure-requests\">
  </head>
<body>
  <div class=\"card\">
    <h1>hCaptcha Demo</h1>
    <p>Это корректная интеграция hCaptcha на стороне фронтенда. Никакой автоматизации/обхода капч здесь нет.</p>
    <form id=\"captcha-form\" method=\"POST\" action=\"/verify\">
      <div class=\"h-captcha\" data-sitekey=\"{key}\"></div>
      <div style=\"margin-top: 12px;\">
        <button type=\"submit\">Отправить</button>
      </div>
    </form>
    <div class=\"result\" id=\"result\"></div>
  </div>

  <script>
    const form = document.getElementById('captcha-form');
    const result = document.getElementById('result');
    form.addEventListener('submit', async (e) => {{
      e.preventDefault();
      result.textContent = 'Проверка...';
      const formData = new FormData(form);
      const res = await fetch('/verify', {{ method: 'POST', body: formData }});
      const text = await res.text();
      result.textContent = text;
    }});
  </script>
</body>
</html>
"""


@app.get("/")
def index() -> Response:
    return Response(_page_html(), mimetype="text/html; charset=utf-8")


@app.post("/verify")
def verify() -> tuple[str, int] | str:
    token = request.form.get("h-captcha-response", "")
    if not token:
        return "Нет токена h-captcha-response", 400

    payload = {
        "secret": _secret(),
        "response": token,
        "remoteip": request.remote_addr,
    }
    try:
        resp = requests.post("https://hcaptcha.com/siteverify", data=payload, timeout=10)
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return f"Ошибка запроса к hcaptcha: {exc}", 500

    if data.get("success") is True:
        return "Успех: токен валиден (серверная валидация пройдена)."
    return f"Ошибка валидации: {data}", 400


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)


