# Como explicar o Repertorio

O Repertorio investiga uma pergunta concreta: fornecer contexto selecionado a partir de familiaridade confirmada e relações conceituais produz referências mais pertinentes que fornecer favoritos? O estudante continua usando seu assistente. Um servidor local guarda repertório e evidências de atividades; o assistente consulta esse servidor por MCP e conduz a explicação.

O protótipo implementa persistência, correção, exportação e restauração. A seleção é determinística. Primeiro veta exclusões, spoilers e familiaridade insuficiente. Depois ordena exemplos por uma combinação explícita de mapeamento conceitual, familiaridade, objetivo e uso relatado. Cada resultado traz o vínculo com o conceito, o limite da analogia e uma sugestão de aplicação. Gostar de uma obra não comprova conhecê-la; uma resposta correta não comprova domínio durável. Se não houver referência apropriada, a orientação é ensinar diretamente.

Há quatro condições técnicas: A sem repertório, B com favoritos, C com seleção completa e D com os mesmos candidatos de C ordenados por tags. B/C mudam tanto a disponibilidade de candidatos quanto sua ordem. D ajuda a separar o efeito do ranking. nDCG mede a qualidade da ordem em relação a rótulos de relevância, sem medir aprendizagem.

O teste inicial possui 31 casos sintéticos e rótulos do mesmo autor assistido por IA que construiu o catálogo. Em 25 casos com referência relevante elegível, a diferença média C−B foi +0,04674. No conjunto reservado por conceito, porém, foi −0,05031 em 12 casos com o desempate fixo por identificador. Essa perda precisa aparecer ao apresentar o projeto. Um diagnóstico posterior, com desempates aleatórios nos três seletores, muda o contraste desse conjunto para +0,15140: até o sinal depende do desempate. O tamanho e a procedência dos casos limitam a conclusão; a avaliação não demonstra superioridade geral. Os pesos, rótulos e resultados originais foram preservados.

A evidência de engenharia é diferente: dois transportes funcionam; clientes autorizados compartilham o perfil; correções mudam a próxima seleção; escritas conflitantes são recusadas. Claude Code criou um item e Codex o corrigiu numa sessão posterior. Testes locais, transcrições sintéticas reais e a instalação do pacote permitem reproduzir essas afirmações no ambiente registrado.

O próximo teste de pesquisa exige revisão especializada dos mapeamentos e rótulos independentes, depois uma comparação controlada do comportamento do tutor. O protocolo de piloto com adultos está preparado, com problemas novos sem assistência e regras de análise, mas não houve recrutamento nem dados de estudantes. Os dados artificiais do piloto servem para exercitar o cálculo.

A contribuição pessoal registrada até aqui é a formulação do produto e de suas restrições. A implementação, os testes e os materiais foram produzidos com assistência de IA. Antes de apresentar o projeto como trabalho próprio, o responsável deve reproduzir os comandos, explicar os mecanismos e limitações e registrar as decisões e experimentos que conduziu pessoalmente. O histórico técnico não substitui essa participação.

Para conferir as afirmações, comece por docs/verification.md, docs/evaluation.md, docs/pilot.md e docs/contribution.md; os resultados regeneráveis ficam em evidence/. A publicação v0.1.0 usa MIT; o registro da release está em docs/publication.md.
