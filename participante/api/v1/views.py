import datetime
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action

from ...models import (
    DocumentoFiscal, Profile, PostoTrabalho, RegistroJornada, Campanha,
    SystemPermission, SystemRole
)
from cupom.models import Cupom
from lojista.models import Lojista
from rest_framework.permissions import AllowAny
from .serializers import (
    DocumentoSerializer, 
    ProfileSerializer, 
    PostoTrabalhoSerializer, 
    RegistroJornadaSerializer,
    CampanhaSerializer,
    SystemPermissionSerializer,
    SystemRoleSerializer,
    ColaboradorSerializer
)


class CampanhaAtivaView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        campanha = Campanha.objects.filter(ativa=True).first()
        if campanha:
            serializer = CampanhaSerializer(campanha)
            return Response(serializer.data)
        return Response({"error": "Nenhuma campanha ativa encontrada"}, status=404)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        is_colaboradores = self.request.query_params.get("colaboradores")
        if is_colaboradores == "true":
            queryset = queryset.filter(is_colaborador=True)
        return queryset

    def get_serializer_class(self):
        is_colaboradores = self.request.query_params.get("colaboradores")
        if is_colaboradores == "true" or self.action == 'retrieve':
            return ColaboradorSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({"error": "Perfil de usuário não configurado no backend"}, status=404)
        
        # Consolida as permissões do usuário
        permissoes = profile.get_all_permissions()
        
        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "nome": profile.nome or request.user.get_full_name() or request.user.username,
            "is_colaborador": profile.is_colaborador,
            "is_superuser": request.user.is_superuser,
            "is_staff": request.user.is_staff,
            "posto_trabalho": profile.posto_trabalho.nome if profile.posto_trabalho else None,
            "posto_trabalho_id": profile.posto_trabalho.id if profile.posto_trabalho else None,
            "permissions": permissoes
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_permissions(self, request, pk=None):
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Sem permissão para alterar acessos"}, status=403)
            
        profile = self.get_object()
        
        new_role_id = request.data.get("role_id")
        adicionais_codenames = request.data.get("permissoes_adicionais", [])
        excluidas_codenames = request.data.get("permissoes_excluidas", [])
        
        # 1. Atualizar o grupo (Role) do Django
        from django.contrib.auth.models import Group
        if new_role_id:
            try:
                group = Group.objects.get(id=new_role_id)
                profile.user.groups.clear()
                profile.user.groups.add(group)
            except Group.DoesNotExist:
                return Response({"error": "Role/Grupo não encontrado"}, status=400)
                
        # 2. Atualizar permissões adicionais
        if isinstance(adicionais_codenames, list):
            perms = SystemPermission.objects.filter(codename__in=adicionais_codenames)
            profile.permissoes_adicionais.set(perms)
            
        # 3. Atualizar permissões excluídas
        if isinstance(excluidas_codenames, list):
            perms = SystemPermission.objects.filter(codename__in=excluidas_codenames)
            profile.permissoes_excluidas.set(perms)
            
        profile.save()
        return Response({"status": "Permissões atualizadas com sucesso"})

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def cadastrar_colaborador(self, request):
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Sem permissão para cadastrar colaboradores"}, status=403)
            
        username = request.data.get("username")
        email = request.data.get("email")
        senha = request.data.get("senha")
        nome = request.data.get("nome")
        cpf = request.data.get("cpf")
        role_id = request.data.get("role_id")
        posto_trabalho_id = request.data.get("posto_trabalho_id")

        if not all([username, email, senha, nome, cpf]):
            return Response({"error": "Todos os campos obrigatórios devem ser preenchidos (username, email, senha, nome, cpf)"}, status=400)

        # Normalizar e Validar CPF
        cpf_digits = ''.join(ch for ch in (cpf or '') if ch.isdigit())
        if len(cpf_digits) != 11:
            return Response({"error": "CPF deve conter 11 dígitos."}, status=400)

        # Formatar CPF
        cpf_formatado = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"

        # Verificar unicidade
        if User.objects.filter(username=username).exists():
            return Response({"error": "Este nome de usuário já está em uso."}, status=400)
            
        if User.objects.filter(email=email).exists():
            return Response({"error": "Este e-mail já está em uso."}, status=400)

        if Profile.objects.filter(CPF=cpf_formatado).exists():
            return Response({"error": "Já existe um colaborador/participante cadastrado com este CPF."}, status=400)

        # Criar Usuário Django
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()
        new_user = UserModel.objects.create_user(
            username=username,
            email=email,
            password=senha,
            is_staff=True
        )

        # Associar Grupo/Role
        from django.contrib.auth.models import Group
        if role_id:
            try:
                group = Group.objects.get(id=role_id)
                new_user.groups.add(group)
            except Group.DoesNotExist:
                pass

        # Criar Perfil (Profile)
        profile = Profile.objects.create(
            user=new_user,
            nome=nome,
            CPF=cpf_formatado,
            is_colaborador=True,
            posto_trabalho_id=posto_trabalho_id if posto_trabalho_id else None,
            status_ativo=True
        )

        return Response({
            "status": "Colaborador cadastrado com sucesso",
            "colaborador": {
                "id": profile.id,
                "nome": profile.nome,
                "username": new_user.username,
                "cpf": profile.CPF
            }
        })


class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = DocumentoFiscal.objects.all()
    serializer_class = DocumentoSerializer
    permission_classes = [IsAuthenticated]


class TestJWTView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "JWT authentication sucessful"})


class IsStaffOrSuperuser(BasePermission):
    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or request.user.is_superuser)


class AdminDashboardMetricsView(APIView):
    permission_classes = [IsAuthenticated, IsStaffOrSuperuser]

    def get(self, request):
        # 1. Estatísticas Gerais
        total_participantes = Profile.objects.count()
        total_cupons = Cupom.objects.count()
        total_notas = DocumentoFiscal.objects.count()
        total_lojistas = Lojista.objects.filter(ativo=True).count()

        # 2. Visão Geral Mensal (Últimos 12 meses)
        monthly_overview = []
        today = datetime.date.today()
        month_names = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        
        for i in range(11, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1
            
            nome_mes = month_names[month - 1]
            
            notas_count = DocumentoFiscal.objects.filter(
                dataDocumento__year=year, 
                dataDocumento__month=month
            ).count()
            
            cupons_count = Cupom.objects.filter(
                dataCriacao__year=year,
                dataCriacao__month=month
            ).count()
            
            monthly_overview.append({
                "mes": nome_mes,
                "notas": notas_count,
                "cupons": cupons_count
            })

        # 3. Produtividade Semanal (Últimos 7 dias)
        weekly_productivity = []
        day_names = ["D", "S", "T", "Q", "Q", "S", "S"]
        for i in range(6, -1, -1):
            day_date = today - datetime.timedelta(days=i)
            day_idx = int(day_date.strftime('%w'))
            
            cupons_dia = Cupom.objects.filter(
                dataCriacao__date=day_date
            ).count()
            
            weekly_productivity.append({
                "label": day_names[day_idx],
                "count": cupons_dia
            })

        # 4. Status dos Postos de Trabalho
        postos_status = []
        for p in PostoTrabalho.objects.all()[:5]:
            postos_status.append({
                "nome": p.nome,
                "status": "Ativo"
            })

        if not postos_status:
            postos_status = [
                {"nome": "Posto 1 - Centro", "status": "Ativo"},
                {"nome": "Posto 2 - Shopping", "status": "Ativo"},
                {"nome": "Posto 3 - Norte", "status": "Ativo"}
            ]

        data = {
            "stats": {
                "participantes": total_participantes,
                "cupons": total_cupons,
                "notas": total_notas,
                "lojistas": total_lojistas
            },
            "monthly_overview": monthly_overview,
            "weekly_productivity": weekly_productivity,
            "postos_status": postos_status
        }
        
        return Response(data)


class PostoTrabalhoViewSet(viewsets.ModelViewSet):
    queryset = PostoTrabalho.objects.all().order_by("nome")
    serializer_class = PostoTrabalhoSerializer
    permission_classes = [IsAuthenticated]


class BaterPontoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        acao = request.data.get("acao")
        profile = getattr(request.user, "profile", None)
        posto_trabalho = profile.posto_trabalho if profile else None

        if acao == "iniciar":
            jornada_ativa = RegistroJornada.objects.filter(
                user=request.user, horario_fim__isnull=True
            ).exists()

            if jornada_ativa:
                return Response(
                    {"error": "Já existe uma jornada ativa para o usuário"}, status=400
                )

            registro = RegistroJornada.objects.create(
                user=request.user,
                posto_trabalho=posto_trabalho,
                horario_inicio=timezone.now(),
            )
            serializer = RegistroJornadaSerializer(registro)
            return Response({"status": "iniciado", "registro": serializer.data})

        elif acao == "finalizar":
            jornada = RegistroJornada.objects.filter(
                user=request.user, horario_fim__isnull=True
            ).first()

            if jornada:
                jornada.horario_fim = timezone.now()
                jornada.save()
                serializer = RegistroJornadaSerializer(jornada)
                return Response({"status": "finalizado", "registro": serializer.data})
            else:
                return Response(
                    {"error": "Nenhuma jornada ativa encontrada para finalizar"},
                    status=400,
                )

        return Response({"error": "Ação inválida ou método não permitido"}, status=400)


class HistoricoPontoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        registros = RegistroJornada.objects.filter(user=request.user).order_by("-horario_inicio")
        serializer = RegistroJornadaSerializer(registros, many=True)
        return Response(serializer.data)


class SystemPermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SystemPermission.objects.all().order_by("category", "name")
    serializer_class = SystemPermissionSerializer
    permission_classes = [IsAuthenticated]


class SystemRoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SystemRole.objects.all().order_by("name")
    serializer_class = SystemRoleSerializer
    permission_classes = [IsAuthenticated]
