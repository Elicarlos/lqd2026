from django.contrib.auth.models import Group

def postos_disponiveis(request):
    """Context processor para disponibilizar postos de trabalho em todos os templates"""
    from participante.models import PostoTrabalho
    
    postos = PostoTrabalho.objects.all().order_by('nome')
    
    return {
        'postos_disponiveis': postos
    }

def documentos_revertidos(request):
    """Context processor para verificar quais documentos já foram revertidos pelo grupo do usuário"""
    if request.user.is_authenticated:
        from participante.models import ReversaoImpressao
        from participante.permissions import is_suporte, is_operador, is_backoffice
        
        # Se for suporte, não mostrar como revertido (pode reverter ilimitado)
        if is_suporte(request.user):
            return {
                'documentos_revertidos_ids': []
            }
        
        # Para Operador e Backoffice, verificar se qualquer usuário do mesmo grupo já reverteu
        if is_operador(request.user) or is_backoffice(request.user):
            # Buscar todos os usuários do mesmo grupo
            grupo_atual = request.user.groups.first()
            if grupo_atual:
                usuarios_do_grupo = grupo_atual.user_set.all()
                
                # Buscar IDs dos documentos que qualquer usuário do grupo já reverteu
                documentos_revertidos_ids = ReversaoImpressao.objects.filter(
                    usuario__in=usuarios_do_grupo
                ).values_list('documento_id', flat=True).distinct()
                
                return {
                    'documentos_revertidos_ids': list(documentos_revertidos_ids)
                }
        
        # Para outros grupos, não mostrar como revertido (sem permissão)
        return {
            'documentos_revertidos_ids': []
        }
    
    return {
        'documentos_revertidos_ids': []
    }
