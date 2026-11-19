from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('pagamentos/', views.pagamentos, name='pagamentos'),
    path('dados-pessoais/', views.dados_pessoais, name='dados_pessoais'),
    path('disciplinas/', views.disciplinas, name='disciplinas'),
    path('documentos/', views.documentos, name='documentos'),
    path('certificados/', views.certificados, name='certificados'),
    path('certificados/<int:certificado_id>/download/', views.download_certificado, name='download_certificado'),
    path('documentos/<str:protocolo>/download/', views.download_documento, name='download_documento'),
    path('secretaria/', views.secretaria, name='secretaria'),
    path('notas/', views.notas, name='notas'),
]
