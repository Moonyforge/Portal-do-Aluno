from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import Usuario, Aluno, Matricula, Disciplina, Nota, Pagamento, Aviso, Documento
from .api_client import api_request, api_download, APIError


# ==== VIEW DE LOGIN INTEGRADO AO BACKEND ====
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        senha = request.POST.get("senha", "")

        try:
            tokens = api_request(
                "auth/login/",
                method="POST",
                data={"email": email, "password": senha},
            )

            perfil = api_request("me/", token=tokens["access"])

            nome = " ".join(
                parte for parte in [
                    perfil.get("first_name", ""),
                    perfil.get("last_name", ""),
                ] if parte
            ) or perfil.get("username", email)

            request.session["api_access"] = tokens["access"]
            request.session["api_refresh"] = tokens["refresh"]
            request.session["api_user"] = perfil
            request.session["usuario_id"] = perfil["id"]
            request.session["usuario_nome"] = nome
            request.session["usuario_tipo"] = perfil.get("role", "").lower()

            if perfil.get("role") in ("STAFF", "ADMIN"):
                return redirect("secretaria")
            return redirect("dashboard")

        except APIError as error:
            if error.status == 401:
                messages.error(request, "E-mail ou senha inválidos.")
            else:
                messages.error(
                    request,
                    "Não foi possível acessar o portal. Tente novamente.",
                )

    return render(request, "login.html")


# ==== VIEW DO DASHBOARD INTEGRADO AO BACKEND ====
def dashboard(request):
    access = request.session.get("api_access")
    perfil = request.session.get("api_user")

    if not access or not perfil:
        return redirect("login")

    if perfil.get("role") != "STUDENT":
        return render(request, "acesso_negado.html")

    try:
        dados = api_request("dashboard/", token=access)
    except APIError as error:
        if error.status == 401:
            request.session.flush()
            return redirect("login")
        messages.error(request, "Não foi possível carregar os dados do portal.")
        dados = {}

    estudante = perfil.get("student") or {}

    context = {
        "nome": request.session.get("usuario_nome"),
        "matricula": estudante.get("registration_number", ""),
        "curso": estudante.get("course", ""),
        "periodo": "",
        "disciplinas": [],
        "notas": [],
        "pagamentos": [],
        "avisos": [],
        "documentos": [],
        "dashboard_api": dados,
        "solicitacoes_total": dados.get("requests", {}).get("total", 0),
        "certificados_total": dados.get("certificates", 0),
    }

    return render(request, "dashboard.html", context)


def pagamentos(request):
    if not request.session.get("api_access"):
        return redirect("login")

    return render(request, "pagamentos.html", {
        "nome": request.session.get("usuario_nome"),
        "pagamentos": [],
        "mensagem_financeiro": (
            "A área financeira ainda não faz parte desta etapa do Portal do Aluno."
        ),
    })


def dados_pessoais(request):
    access = request.session.get("api_access")
    perfil = request.session.get("api_user")

    if not access or not perfil:
        return redirect("login")

    try:
        perfil = api_request("me/", token=access)
        request.session["api_user"] = perfil
    except APIError as error:
        if error.status == 401:
            request.session.flush()
            return redirect("login")
        messages.error(request, "Não foi possível carregar seus dados pessoais.")

    estudante = perfil.get("student") or {}
    nome = " ".join(
        parte for parte in [
            perfil.get("first_name", ""),
            perfil.get("last_name", ""),
        ] if parte
    ) or perfil.get("username", "")

    aluno = {
        "usuario": {
            "nome": nome,
            "email": perfil.get("email", ""),
        },
        "matricula": estudante.get("registration_number", "Não informado"),
        "curso": estudante.get("course", "Não informado"),
        "periodo": "Não informado",
    }

    return render(request, "dados_pessoais.html", {
        "aluno": aluno,
        "nome": nome,
    })


def disciplinas(request):
    if not request.session.get("api_access"):
        return redirect("login")

    return render(request, "disciplinas.html", {
        "disciplinas": [],
        "nome": request.session.get("usuario_nome"),
        "mensagem_academica": (
            "A consulta de disciplinas depende da integração com o sistema acadêmico, "
            "que ainda está pendente."
        ),
    })


def documentos(request):
    access = request.session.get("api_access")
    perfil = request.session.get("api_user")

    if not access or not perfil:
        return redirect("login")

    try:
        tipos = api_request("documentos/tipos/", token=access)

        if request.method == "POST":
            tipo_id = request.POST.get("document_type")
            tipo = next(
                (item for item in tipos if str(item["id"]) == str(tipo_id)),
                None,
            )

            if not tipo:
                messages.error(request, "Selecione um tipo de documento válido.")
            else:
                dados = {
                    campo: request.POST.get(f"campo_{campo}", "").strip()
                    for campo in tipo.get("required_fields", [])
                }

                resultado = api_request(
                    "documentos/solicitacoes/",
                    method="POST",
                    token=access,
                    data={
                        "document_type": int(tipo_id),
                        "data": dados,
                    },
                )

                messages.success(
                    request,
                    f"Solicitação registrada! Protocolo: {resultado['protocol']}",
                )
                return redirect("documentos")

        resposta = api_request(
            "documentos/solicitacoes/",
            token=access,
        )
        solicitacoes = (
            resposta.get("results", [])
            if isinstance(resposta, dict)
            else resposta
        )

    except APIError as error:
        if error.status == 401:
            request.session.flush()
            return redirect("login")

        messages.error(
            request,
            "Não foi possível carregar ou enviar sua solicitação. Verifique os dados e tente novamente.",
        )
        tipos = []
        solicitacoes = []

    context = {
        "nome": request.session.get("usuario_nome"),
        "tipos_documento": tipos,
        "documentos": solicitacoes,
    }

    return render(request, "documentos.html", context)


def notas(request):
    if not request.session.get("api_access"):
        return redirect("login")

    return render(request, "notas.html", {
        "notas": [],
        "nome": request.session.get("usuario_nome"),
        "mensagem_academica": (
            "A consulta de notas depende da integração com o sistema acadêmico, "
            "que ainda está pendente."
        ),
    })


# ==== VIEW DE LOGOUT ====
def logout_view(request):
    request.session.flush()
    return redirect('login')



# ==== PAINEL DA SECRETARIA ====
def secretaria(request):
    access = request.session.get("api_access")
    perfil = request.session.get("api_user")

    if not access or not perfil:
        return redirect("login")

    if perfil.get("role") not in ("STAFF", "ADMIN"):
        return render(request, "acesso_negado.html")

    if request.method == "POST":
        protocolo = request.POST.get("protocolo", "").strip()
        acao = request.POST.get("acao", "status")

        if acao in ("aluno", "editar_aluno", "desativar_aluno", "reativar_aluno"):
            aluno_id = request.POST.get("aluno_id", "").strip()
            dados = {
                "first_name": request.POST.get("nome", "").strip(),
                "last_name": request.POST.get("sobrenome", "").strip(),
                "email": request.POST.get("email", "").strip(),
                "registration_number": request.POST.get("matricula", "").strip(),
                "course": request.POST.get("curso", "").strip(),
            }
            try:
                if acao == "desativar_aluno":
                    api_request(
                        f"admin/alunos/{aluno_id}/",
                        method="PATCH", token=access,
                        data={"is_active": False},
                    )
                    messages.success(request, "Aluno desativado.")
                elif acao == "reativar_aluno":
                    api_request(
                        f"admin/alunos/{aluno_id}/",
                        method="PATCH", token=access,
                        data={"is_active": True},
                    )
                    messages.success(request, "Acesso do aluno reativado.")
                elif acao == "editar_aluno":
                    senha = request.POST.get("senha", "")
                    if senha:
                        dados["password"] = senha
                    api_request(
                        f"admin/alunos/{aluno_id}/",
                        method="PATCH", token=access, data=dados,
                    )
                    messages.success(request, "Cadastro atualizado.")
                else:
                    dados["password"] = request.POST.get("senha", "")
                    api_request(
                        "admin/alunos/", method="POST",
                        token=access, data=dados,
                    )
                    messages.success(request, "Aluno cadastrado.")
            except APIError as error:
                if error.status == 401:
                    request.session.flush()
                    return redirect("login")
                messages.error(request, f"Não foi possível salvar o aluno: {error.data}")
            return redirect("secretaria")


        if acao == "editar_certificado":
            certificado_id = request.POST.get("certificado_id", "").strip()
            dados = {
                "student": request.POST.get("matricula", "").strip(),
                "category": request.POST.get("categoria", "").strip(),
                "title": request.POST.get("titulo", "").strip(),
                "description": request.POST.get("descricao", "").strip(),
            }
            arquivo = request.FILES.get("arquivo_certificado")

            if not all([certificado_id, dados["student"], dados["category"], dados["title"]]):
                messages.error(request, "Preencha matrícula, categoria e identificação.")
            else:
                try:
                    api_request(
                        f"admin/certificados/{certificado_id}/",
                        method="PATCH",
                        token=access,
                        data=dados,
                        files={"file": arquivo} if arquivo else None,
                    )
                    messages.success(request, "Certificado atualizado com sucesso.")
                except APIError as error:
                    if error.status == 401:
                        request.session.flush()
                        return redirect("login")
                    messages.error(request, f"Não foi possível atualizar o certificado. Detalhes: {error.data}")

            return redirect("secretaria")

        if acao == "certificado":
            dados = {
                "student": request.POST.get("matricula", "").strip(),
                "category": request.POST.get("categoria", "").strip(),
                "title": request.POST.get("titulo", "").strip(),
                "description": request.POST.get("descricao", "").strip(),
            }
            arquivo = request.FILES.get("arquivo_certificado")

            if not all([dados["student"], dados["category"], dados["title"], arquivo]):
                messages.error(request, "Preencha matrícula, categoria, identificação e selecione o arquivo.")
            else:
                try:
                    api_request(
                        "admin/certificados/",
                        method="POST",
                        token=access,
                        data=dados,
                        files={"file": arquivo},
                    )
                    messages.success(request, "Certificado cadastrado com sucesso.")
                except APIError as error:
                    if error.status == 401:
                        request.session.flush()
                        return redirect("login")
                    messages.error(request, f"Não foi possível cadastrar. Verifique a matrícula e o arquivo. Detalhes: {error.data}")

            return redirect("secretaria")

        try:
            if acao == "upload":
                arquivo = request.FILES.get("arquivo_pdf")
                if not arquivo:
                    messages.error(request, "Selecione um arquivo PDF.")
                elif not arquivo.name.lower().endswith(".pdf"):
                    messages.error(request, "Envie somente arquivos PDF.")
                else:
                    api_request(
                        f"admin/solicitacoes/{protocolo}/arquivo/",
                        method="POST",
                        token=access,
                        files={"file": arquivo},
                    )
                    messages.success(request, f"PDF anexado à solicitação {protocolo}.")

            else:
                status = request.POST.get("status", "").strip()
                observacao = request.POST.get("observacao", "").strip()
                api_request(
                    f"admin/solicitacoes/{protocolo}/estado/",
                    method="PATCH",
                    token=access,
                    data={"status": status, "note": observacao},
                )
                messages.success(request, f"Solicitação {protocolo} atualizada.")

        except APIError as error:
            if error.status == 401:
                request.session.flush()
                return redirect("login")
            messages.error(request, "Não foi possível concluir a operação. Verifique o arquivo e o status.")

        return redirect("secretaria")

    try:
        resposta = api_request("admin/solicitacoes/", token=access)
        solicitacoes = resposta.get("results", []) if isinstance(resposta, dict) else resposta

        rotulos_status = {
            "RECEIVED": "Recebida",
            "IN_REVIEW": "Em análise",
            "AWAITING_INFO": "Aguardando informação",
            "COMPLETED": "Concluída",
            "REJECTED": "Indeferida",
        }

        for item in solicitacoes:
            permitidos = item.get("allowed_transitions", [])
            atual = item.get("status")
            item["status_choices"] = [
                (valor, rotulo)
                for valor, rotulo in rotulos_status.items()
                if valor in permitidos or valor == atual
            ]

    except APIError as error:
        if error.status == 401:
            request.session.flush()
            return redirect("login")
        messages.error(request, "Não foi possível carregar as solicitações.")
        solicitacoes = []

    try:
        resposta_certificados = api_request("admin/certificados/", token=access)
        certificados = (
            resposta_certificados.get("results", [])
            if isinstance(resposta_certificados, dict)
            else resposta_certificados
        )
    except APIError as error:
        certificados = []
        if error.status == 401:
            request.session.flush()
            return redirect("login")
        messages.error(request, "Não foi possível carregar os certificados.")

    try:
        resposta_alunos = api_request("admin/alunos/", token=access)
        alunos = (
            resposta_alunos.get("results", [])
            if isinstance(resposta_alunos, dict)
            else resposta_alunos
        )
    except APIError as error:
        alunos = []
        if error.status == 401:
            request.session.flush()
            return redirect("login")
        messages.error(request, "Não foi possível carregar os alunos.")

    return render(request, "secretaria.html", {
        "nome": request.session.get("usuario_nome"),
        "solicitacoes": solicitacoes,
        "certificados": certificados,
        "alunos": alunos,
    })



def download_documento(request, protocolo):
    access = request.session.get("api_access")
    perfil = request.session.get("api_user")

    if not access or not perfil:
        return redirect("login")

    if perfil.get("role") != "STUDENT":
        return render(request, "acesso_negado.html")

    try:
        conteudo, tipo = api_download(
            f"documentos/solicitacoes/{protocolo}/arquivo/",
            access,
        )
        resposta = HttpResponse(conteudo, content_type=tipo)
        resposta["Content-Disposition"] = f'attachment; filename="{protocolo}.pdf"'
        return resposta

    except APIError as error:
        if error.status == 401:
            request.session.flush()
            return redirect("login")
        messages.error(request, "Não foi possível baixar este documento.")
        return redirect("documentos")


def certificados(request):
    access = request.session.get("api_access")
    perfil = request.session.get("api_user")

    if not access or not perfil:
        return redirect("login")

    if perfil.get("role") != "STUDENT":
        return render(request, "acesso_negado.html")

    try:
        resposta = api_request("certificados/", token=access)
        lista = resposta.get("results", []) if isinstance(resposta, dict) else resposta
    except APIError as error:
        if error.status == 401:
            request.session.flush()
            return redirect("login")
        messages.error(request, "Não foi possível carregar seus certificados.")
        lista = []

    return render(request, "certificados.html", {
        "nome": request.session.get("usuario_nome"),
        "certificados": lista,
    })


def download_certificado(request, certificado_id):
    access = request.session.get("api_access")
    perfil = request.session.get("api_user")

    if not access or not perfil:
        return redirect("login")

    if perfil.get("role") != "STUDENT":
        return render(request, "acesso_negado.html")

    try:
        conteudo, tipo = api_download(
            f"certificados/{certificado_id}/download/", access
        )
        resposta = HttpResponse(conteudo, content_type=tipo)
        resposta["Content-Disposition"] = (
            f'attachment; filename="certificado-{certificado_id}"'
        )
        return resposta
    except APIError as error:
        if error.status == 401:
            request.session.flush()
            return redirect("login")
        messages.error(request, "Não foi possível baixar este certificado.")
        return redirect("certificados")
