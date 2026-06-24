import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import RegistroJornada

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def inicia_jornada_login(sender, request, user, **kwargs):
    if not user or not user.is_superuser:
        return

    logger.info(
        f"Signal de login recebido para {user.username} (superuser: {user.is_superuser})"
    )

    try:
        # Verifica se já existe uma jornada ativa hoje
        hoje = timezone.now().date()
        jornada_ativa = RegistroJornada.objects.filter(
            user=user, horario_inicio__date=hoje, horario_fim__isnull=True
        ).first()

        if (
            not jornada_ativa
            and hasattr(user, "profile")
            and user.profile.posto_trabalho
        ):
            jornada = RegistroJornada.objects.create(
                user=user,
                posto_trabalho=user.profile.posto_trabalho,
                horario_inicio=timezone.now(),
            )
            logger.info(
                f"Jornada {jornada.id} iniciada automaticamente para {user.username}"
            )
            request.session["last_activity"] = timezone.now().timestamp()
        else:
            if jornada_ativa:
                logger.warning(
                    f"Jornada {jornada_ativa.id} já ativa para {user.username}"
                )
            else:
                logger.warning(
                    f"Usuário {user.username} sem posto de trabalho definido"
                )
    except Exception as e:
        logger.error(f"Erro ao iniciar jornada no signal de login: {str(e)}")


# DESABILITADO: Finalização automática da jornada no logout
# @receiver(user_logged_out)
# def finaliza_jornada_logout(sender, request, user, **kwargs):
#     """
#     DESABILITADO: Não finaliza mais a jornada automaticamente no logout
#     Permite que o usuário faça logout e login novamente sem perder a jornada ativa
#     """
#     pass


# def setup_dashboard_cards_auto():
#     """
#     Cria automaticamente os cards do dashboard e grupos se não existirem.
#     Esta função é chamada automaticamente sem precisar de comandos manuais.
#     DESABILITADO - Agora usando o novo sistema CardDinamico
#     """
#     pass


# @receiver(user_logged_in)
# def ensure_dashboard_cards_exist(sender, request, user, **kwargs):
#     """
#     Garante que os cards do dashboard existam sempre que alguém fizer login.
#     """
#     setup_dashboard_cards_auto()


@receiver(user_logged_in)
def ensure_groups_exist(sender, request, user, **kwargs):
    """
    Garante que os grupos necessários existam sempre que alguém fizer login.
    """
    try:
        from django.contrib.auth.models import Group
        
        # Grupos que devem existir no sistema
        grupos_necessarios = [
            "Operador",
            "Operadores", 
            "Backoffice",
            "Supervisor",
            "Gerente",
            "Gerente Solve",
            "Suporte"
        ]
        
        grupos_criados = []
        for nome_grupo in grupos_necessarios:
            grupo, created = Group.objects.get_or_create(name=nome_grupo)
            if created:
                grupos_criados.append(nome_grupo)
                logger.info(f"Grupo criado automaticamente: {nome_grupo}")
        
        if grupos_criados:
            logger.info(f"Grupos criados automaticamente: {', '.join(grupos_criados)}")
            
    except Exception as e:
        logger.error(f"Erro ao criar grupos automaticamente: {str(e)}")


@receiver(user_logged_in)
def sync_user_roles_with_groups(sender, request, user, **kwargs):
    """
    Sincroniza UserRoles com grupos Django automaticamente.
    """
    try:
        from django.contrib.auth.models import Group
        from participante.models import UserRole
        
        # Verificar se o usuário tem UserRoles
        user_roles = UserRole.objects.filter(user=user)
        
        for user_role in user_roles:
            role_name = user_role.role.name
            
            # Verificar se o grupo existe
            try:
                grupo = Group.objects.get(name=role_name)
                
                # Adicionar usuário ao grupo se não estiver
                if not user.groups.filter(name=role_name).exists():
                    user.groups.add(grupo)
                    logger.info(f"Usuário {user.username} adicionado ao grupo {role_name}")
                    
            except Group.DoesNotExist:
                # Criar o grupo se não existir
                grupo = Group.objects.create(name=role_name)
                user.groups.add(grupo)
                logger.info(f"Grupo {role_name} criado e usuário {user.username} adicionado")
                
    except Exception as e:
        logger.error(f"Erro ao sincronizar UserRoles com grupos: {str(e)}")


@receiver(user_logged_in)
def report_user_cards_access(sender, request, user, **kwargs):
    """
    Reporta automaticamente quais cards o usuário tem acesso baseado em seus grupos.
    """
    try:
        from participante.models import RoleCard, SystemRole, DashboardCard
        from django.db.models import Count
        
        # Só reporta para superuser ou staff (para não poluir o log)
        if not (user.is_superuser or user.is_staff):
            return
            
        logger.info(f"🔍 REPORTE AUTOMÁTICO - Usuário: {user.username}")
        
        # Verificar grupos do usuário
        grupos_usuario = [g.name for g in user.groups.all()]
        logger.info(f"📋 Grupos do usuário: {grupos_usuario}")
        
        # Verificar cards por role
        for role in SystemRole.objects.all():
            cards = RoleCard.objects.filter(role=role).select_related('card')
            if cards.exists():
                card_titles = [role_card.card.title for role_card in cards]
                logger.info(f"🎭 Role '{role.name}': {len(cards)} cards - {card_titles}")
        
        # Verificar cards por tipo
        for card_type in ['participantes', 'lojistas', 'configuracoes', 'backoffice', 'relatorios']:
            cards = DashboardCard.objects.filter(card_type=card_type)
            if cards.exists():
                card_titles = [card.title for card in cards]
                logger.info(f"📊 Tipo '{card_type}': {len(cards)} cards - {card_titles}")
        
        # Estatísticas gerais
        total_cards = DashboardCard.objects.count()
        total_roles = SystemRole.objects.count()
        total_associations = RoleCard.objects.count()
        
        logger.info(f"📈 ESTATÍSTICAS: {total_cards} cards, {total_roles} roles, {total_associations} associações")
        
        # Verificar cards sem associação
        cards_sem_associacao = DashboardCard.objects.annotate(
            num_roles=Count('rolecard')
        ).filter(num_roles=0)
        
        if cards_sem_associacao.exists():
            card_titles = [card.title for card in cards_sem_associacao]
            logger.warning(f"⚠️  CARDS SEM ASSOCIAÇÃO: {card_titles}")
        else:
            logger.info("✅ Todos os cards estão associados a pelo menos um role!")
            
    except Exception as e:
        logger.error(f"Erro ao reportar acesso aos cards: {str(e)}")
