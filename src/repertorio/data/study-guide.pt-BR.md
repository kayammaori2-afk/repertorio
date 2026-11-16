# Kit operacional — ainda sem participantes

Comece pela usabilidade com seis adultos; é uma meta operacional inicial escolhida pelo autor, sem alegação de poder estatístico. Só avance para o piloto de aprendizagem depois de corrigir falhas e obter as revisões humanas. Não convide participantes enquanto `study check` apresentar pendências. O comando confere declarações e preenchimento; não verifica a autenticidade de uma aprovação.

## Antes da primeira sessão

1. Complete `study.json`: equipe/contatos, datas, provedor e versão exata do modelo, triagem, retenção/acesso e referências das revisões. Não registre “aprovado” sem revisão realizada. A aplicabilidade da revisão ética deve ser determinada pelo responsável no contexto da instituição.
2. Complete também os campos `activities_and_duration`, `costs_and_compensation`, `provider_data_handling` e `withdrawal_and_limits` em `study.json`. Gere o documento com `repertorio study consent --directory PRIVATE_DIR/pilot` e obtenha revisão humana antes de marcar `consent_text_reviewed`. Para corrigir, edite os campos e gere novamente antes do congelamento; texto arbitrário no arquivo não substitui os campos obrigatórios. Explique exposição ao provedor, voluntariedade, exclusão e limites de cópias. Mantenha contatos/consentimentos separados das respostas pseudonimizadas. O comando não registra consentimento de ninguém.
3. Revise perguntas, rubricas, dificuldade e possível vazamento com especialista em ensino de probabilidade/economia. Treine dois corretores; não forneça a condição experimental a eles.
4. Execute uma sessão técnica com dados artificiais e teste exportação/correção/exclusão. Registre problemas reais. Não contabilize assistentes de IA como participantes.
5. Execute `repertorio study check --directory PRIVATE_DIR/pilot`; depois de resolver tudo, `repertorio study freeze --directory PRIVATE_DIR/pilot`. Arquive o manifesto antes de coletar dados. Isso não é registro público prospectivo.

## Roteiro de usabilidade (aproximadamente 25–35 minutos)

Use o assistente e equipamento que serão relatados. Não salve nomes, histórico completo, gravação ou dados sensíveis por padrão. Gere um código `p-` seguido de 16 dígitos hexadecimais aleatórios por participante, por exemplo com `secrets.token_hex(8)`; guarde a ligação de identidade separadamente. Não insira dados reais no Git.

Peça as tarefas abaixo na ordem. Não demonstre a solução antes da tentativa. Se houver pedido de ajuda, ajude e registre `assisted=True`. Cronometre da instrução até a conclusão ou desistência. Interromper é permitido; não transformar dado ausente em falha ou sucesso inventado.

| Código | Instrução | Critério observado de conclusão |
|---|---|---|
| connect | Conecte o Repertorio seguindo o guia. | O assistente descobre e chama `learning_options`. |
| first_lesson | Escolha um assunto e estude usando uma experiência que você confirme, ou escolha explicação direta. | Recebe explicação e questão de transferência; registre separadamente problemas de conteúdo. |
| resume | Feche a conversa e continue em nova conversa/assistente compatível. | Informações salvas reaparecem sem recadastro. Se nada foi salvo por escolha, registre `not_applicable_no_saved_data`; não force cadastro. |
| correct | Corrija um fato do repertório e verifique a mudança. | Apenas o campo escolhido muda; a consulta seguinte reflete a correção. Se não há registro, marque não aplicável. |
| skip_personalization | Peça para estudar sem responder sobre seu repertório. | A explicação continua sem cadastro compulsório nem familiaridade inventada. |

Registre uma linha por tarefa para TODOS os inscritos, inclusive desistências e tarefas não aplicáveis. `completed` vazio significa não observado/não aplicável; `False` significa tentativa não concluída. `failure_code` explica esses casos (ex.: `connection_failed`, `declined`, `not_attempted`, `not_applicable_no_saved_data`). Não calcule proporções usando só quem terminou. O relatório separa não observado e usa todos os inscritos como denominador. Na decisão de avanço, examine se a ausência de dados salvos explica tarefas não aplicáveis.

Ao final pergunte: “Em que momento ficou confuso?”, “O que precisou repetir?”, “Em qual situação usaria de novo?”. Registre notas desidentificadas num local protegido; o CSV aceita só códigos. Após sete dias, verifique retorno voluntário com consentimento e registre a mesma resposta em todas as linhas da pessoa. Ausência de resposta é vazio, nunca `False` por suposição. Não exija retorno para receber eventual compensação.

Analise com `repertorio study analyze-usability --directory PRIVATE_DIR/pilot`. Antes de ampliar: nenhum defeito crítico de privacidade/perda de dados pendente e pelo menos 5/6 concluindo primeira aula, retomada e correção sem ajuda. Esses critérios são decisões operacionais iniciais, não validação científica; documente desvios antes de alterar a regra.

## Piloto de aprendizagem posterior

Siga `operator/learning-protocol.md`, cópia do protocolo canônico `docs/pilot.md`, que contém desenho A/B/C, duas aulas, rubrica de oito pontos, perdas e análise. A comparação adicional E (perfil simples + prompt) pertence ao experimento de respostas de tutores; não foi silenciosamente adicionada ao desenho humano A/B/C. Qualquer mudança exige nova versão antes de recrutamento.

O CSV `learning.csv` está vazio, no formato do analisador existente. Após coleta legítima e revisão, use `python -m repertorio.pilot --input PRIVATE_DIR/pilot/learning.csv --output PRIVATE_DIR/learning-analysis`. Esse analisador não comprova consentimento nem autorização. Não misture coortes ou dados artificiais. Os 36 participantes planejados são de viabilidade, sem garantia de potência para eficácia.

A alocação real deve usar uma sequência nova e privada, gerada por responsável independente antes da coleta: blocos aleatórios A/B/C dentro de baixo/alto conhecimento inicial (0–4 / 5–8), seis blocos por estrato; alternar ordem dos conceitos entre blocos e balancear formas X/Y dentro de braço/estrato. O responsável revela a próxima alocação só depois de elegibilidade, consentimento e baseline. Não reutilize a semente pública da simulação. Não substitua desistentes depois da randomização.

Entregue apenas `participant/form-baseline.txt` antes das aulas. Entregue X ou Y imediatamente e a forma alternativa após sete dias ± dois. Guarde respostas e `operator/item-bank-with-answers.json` longe do tutor e do participante. O kit remove gabaritos dos formulários; os itens continuam públicos no repositório. Pergunte sobre exposição prévia e registre contaminação: não são testes secretos ou psicometricamente equacionados.

Em `scoring.csv`, preserve avaliações independentes dos dois corretores e uma linha separada de adjudicação. Não sobrescreva originais. Registre cada critério 0/1, erro observado e justificativa; transfira apenas totais adjudicados ao CSV de análise. Retenção ausente continua ausente. Registre datas/intervalos reais e ajuda recebida em log privado.

## Decisões e encerramento

Mantenha registro de triagem, consentimento, inscrição, randomização, retirada e seguimento (`flow.csv`), mesmo quando faltarem resultados. Confira os denominadores com o CSV; o programa não consegue detectar uma pessoa que o operador omitiu inteiramente. Exclua/retenha conforme o plano consentido, incluindo arquivos exportados e histórico do provedor. Não publique microdados ou depoimentos por padrão.

Base metodológica: extensão CONSORT para estudos piloto randomizados, Eldridge et al., BMJ 2016, https://www.bmj.com/content/355/bmj.i5239. Esta é uma adaptação operacional para educação, não certificação de conformidade. Revisões pedagógicas, éticas e resultados reais permanecem pendentes.
