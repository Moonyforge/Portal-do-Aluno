import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class APIError(Exception):
    def __init__(self, status, data):
        self.status = status
        self.data = data
        super().__init__(str(data))


def api_request(path, method="GET", token=None, data=None, files=None):
    base_url = getattr(
        settings,
        "BACKEND_API_URL",
        "http://127.0.0.1:8000/api",
    ).rstrip("/")

    headers = {"Accept": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = None
    if files:
        boundary = uuid.uuid4().hex
        partes = []

        for campo, valor in (data or {}).items():
            partes.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{campo}"\r\n\r\n'
                f"{valor}\r\n"
            .encode("utf-8")
            )

        for campo, arquivo in files.items():
            nome = arquivo.name.rsplit("/", 1)[-1].replace('"', "")
            tipo = getattr(arquivo, "content_type", None) or "application/pdf"
            conteudo = arquivo.read()

            partes.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{campo}"; filename="{nome}"\r\n'
                f"Content-Type: {tipo}\r\n\r\n"
            .encode("utf-8") + conteudo + b"\r\n"
            )

        partes.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(partes)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

    elif data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")

    request = Request(
        f"{base_url}/{path.lstrip('/')}",
        data=body,
        headers=headers,
        method=method.upper(),
    )

    try:
        with urlopen(request, timeout=10) as response:
            content = response.read()
            return json.loads(content) if content else None

    except HTTPError as error:
        content = error.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(content)
        except json.JSONDecodeError:
            details = {"detail": "Erro na comunicação com o servidor."}
        raise APIError(error.code, details) from error

    except (URLError, TimeoutError) as error:
        raise APIError(
            503,
            {"detail": "Não foi possível conectar ao servidor do portal."},
        ) from error


def api_download(path, token):
    base_url = getattr(
        settings,
        "BACKEND_API_URL",
        "http://127.0.0.1:8000/api",
    ).rstrip("/")

    request = Request(
        f"{base_url}/{path.lstrip('/')}",
        headers={
            "Accept": "application/pdf",
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=15) as response:
            return response.read(), response.headers.get("Content-Type", "application/pdf")

    except HTTPError as error:
        content = error.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(content)
        except json.JSONDecodeError:
            details = {"detail": "Não foi possível baixar o documento."}
        raise APIError(error.code, details) from error

    except (URLError, TimeoutError) as error:
        raise APIError(
            503,
            {"detail": "Não foi possível conectar ao servidor do portal."},
        ) from error
