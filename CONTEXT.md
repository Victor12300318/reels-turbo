# Clonify AI

Contexto de clonagem e automação de Reels do Instagram com biblioteca local de vídeos.

## Language

### Distribuição de vídeos

**Rotação estrita**:
Regra de distribuição em que um vídeo da biblioteca local não pode ser reutilizado até que todos os vídeos elegíveis tenham sido usados uma vez no ciclo atual.
_Avoid_: Anti-repetição, distribuição aleatória

**Ciclo do usuário**:
A sequência independente de vídeos elegíveis pertencentes a um usuário; a biblioteca global é apenas reserva quando o usuário não possui vídeos próprios.
_Avoid_: Ciclo global, rotação compartilhada

**Ciclo concluído**:
Estado em que todos os vídeos elegíveis do usuário já foram usados no ciclo atual; a próxima clonagem inicia um novo ciclo automaticamente.
_Avoid_: Reinício manual, bloqueio de produção

**Vídeo elegível**:
Vídeo do usuário com arquivo existente e análise concluída; não exige compatibilidade prévia com o Reels de referência para entrar no ciclo.
_Avoid_: Vídeo compatível, vídeo similar

**Uso no ciclo**:
Consumo de um vídeo elegível no ciclo do usuário, contado somente quando o vídeo final é gerado com sucesso; falhas não consomem o vídeo.
_Avoid_: Seleção da IA, tentativa de uso

### Estilo do texto

**Preferência de estilo**:
Padrão salvo pelo usuário para fonte, cor e fundo do texto sobreposto; vale para todas as próximas clonagens e substitui o estilo detectado no Reels de referência nos campos escolhidos.
_Avoid_: Estilo da IA, template do vídeo, escolha por job

**Catálogo de fontes**:
Conjunto curado de famílias tipográficas gratuitas oferecidas na preferência de estilo e garantidas no ambiente de renderização.
_Avoid_: Fonte customizada, upload de fonte

**Cor do texto**:
Cor escolhida entre as cores padrão do sistema ou definida como cor customizada pelo usuário.
_Avoid_: Cor livre, cor da IA

**Modo de fundo**:
Escolha do usuário entre sem fundo, caixa branca ou caixa preta atrás do texto sobreposto.
_Avoid_: Opacidade, contorno do texto

**Pré-visualização de estilo**:
Exibição imediata do texto sobreposto com a preferência de estilo escolhida, antes de salvar.
_Avoid_: Vídeo de teste, render de exemplo

**Estilo padrão**:
Preferência inicial de um usuário que nunca escolheu estilo: fonte padrão do sistema, texto branco e sem caixa de fundo.
_Avoid_: Estilo da IA, campos vazios

**Posição automática**:
Posição e tamanho do texto definidos pelas regras de zona segura do vídeo, sem escolha do usuário.
_Avoid_: Preferência de posição, escolha de tamanho

### Publicação e Entrega

**Destino de entrega**:
Canal de saída configurado pelo usuário para receber o vídeo processado (Instagram ou Telegram).
_Avoid_: Tipo de postagem, modo de exportação

**Despacho para Telegram**:
Envio imediato do arquivo de vídeo renderizado para o canal do Telegram configurado pelo usuário, contornando a fila de agendamento do Instagram.
_Avoid_: Notificação de conclusão, webhook do Telegram

**Postagem exatamente única**:
Garantia de que um job resulta em no máximo uma publicação no Instagram, tanto no agendamento quanto na publicação manual; um resultado incerto bloqueia novas tentativas até ser resolvido.
_Avoid_: Publicação duplicada, tentar até conseguir

**Publicação incerta**:
Estado de um job cuja tentativa de publicação já foi enviada, mas cujo resultado é desconhecido; a retentativa automática fica bloqueada até resolução no painel.
_Avoid_: Falha de publicação, job pendente

**Resolução de publicação incerta**:
Decisão do usuário entre confirmar a publicação que ocorreu ou descartar a tentativa sem publicar; não retenta a postagem.
_Avoid_: Retry manual, republicar automaticamente

**Selo de uso no ciclo**:
Marca exibida por vídeo na biblioteca indicando se ele já foi usado no ciclo atual.
_Avoid_: Contador de cliques, histórico de views
