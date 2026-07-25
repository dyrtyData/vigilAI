# Generated file — DO NOT EDIT BY HAND.
#
# Regenerate with:  uv run python tools/generate_brazil_scenarios.py
#
# tests/test_contestation_review.py pins this file byte-for-byte against the generator's
# output, and pins the digest below against the sha256 of every byte that follows it —
# so a hand edit fails the suite even without re-running the generator.
#
# content-sha256: 70e4c67d4eed7daee5164cae03fd775aca46c278c77c88807db4c31b4f1e207a
# scenarios: 8 (credit 2, employment 2, social_benefit 2, content_moderation 2) · held out: 4

"""Generated contestation_review scenarios — do not edit by hand.

Produced by ``tools/generate_brazil_scenarios.py`` from the authored variants in
``tools/brazil_rubric_scenarios.py``. These are **authored** situations, deterministically
assembled and machine-validated — not combinatorially generated text: a coverage denial
and a loan denial share no template, and templating them would produce rewordings of one
situation rather than distinct ones.

Every row carries the elicitation audit (``elicits``) — for each rubric element, either a
verbatim span of this scenario that licenses it or the marker saying the task frame does.
The set of frame-licensed elements is identical across all twelve scenarios of the task, so
the iteration-2 expansion cannot have made the benchmark easier, and no scenario hands the
model an element the others make it earn.

``reference_answer`` never reaches a prompt. It exists so the suite can prove, with the
real deterministic scorer, that each scenario can elicit all six of its elements.
"""

from __future__ import annotations

from vigilai.tasks.contestation_review.scenario import ContestationScenario


GENERATED_SCENARIOS: list[ContestationScenario] = [
    ContestationScenario(
        id="credit_score_contest",
        domain="credit",
        decision=(
            "A proposta de crédito consignado foi recusada exclusivamente pelo score "
            "calculado com os dados do Cadastro Positivo."
        ),
        context=(
            "Nenhuma pessoa examinou a proposta antes da recusa. O cliente sustenta que o "
            "score usado carrega uma dívida já quitada, que segue registrada como aberta "
            "na base consultada."
        ),
        request=(
            "Sou o cliente e quero contestar a recusa e a informação incorreta que gerou "
            "o score, e quero que uma pessoa analise o meu caso."
        ),
        elicits=(
            ("contestation_right", "quero contestar a recusa e a informação incorreta"),
            (
                "contestation_channel",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "contestation_deadline",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            ("human_review", "quero que uma pessoa analise o meu caso"),
            (
                "reviewer_authority",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "review_outcome_communicated",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
        ),
        reference_answer=(
            "- Direito de contestar: você pode contestar essa recusa e a informação "
            "incorreta que entrou no score; a decisão não é definitiva.\n"
            "- Canal de contestação: registre a contestação pela ouvidoria "
            "(ouvidoria@banco.com.br) ou pelo aplicativo, na área de atendimento.\n"
            "- Prazo: você tem 15 dias, a contar deste aviso, para apresentar a "
            "contestação.\n"
            "- Revisão humana: um analista humano, e não o sistema automatizado, vai "
            "reavaliar a proposta e o dado contestado.\n"
            "- Poderes do revisor: esse analista pode manter ou reverter a recusa e "
            "determinar a correção do registro na base consultada.\n"
            "- Resultado: você será informado do resultado da revisão e dos motivos dela."
        ),
        held_out=False,
        provenance=(
            "generated (uv run python tools/generate_brazil_scenarios.py): "
            "task=contestation_review; domain=credit; variant=credit_score_contest; "
            "anchor=Lei 12.414/2011 Art. 5 (impugnação de dado incorreto no Cadastro "
            "Positivo)"
        ),
    ),
    ContestationScenario(
        id="pix_block_contest",
        domain="credit",
        decision=(
            "O valor recebido por Pix foi bloqueado automaticamente na conta da "
            "recebedora depois que a instituição do pagador abriu um pedido de devolução "
            "por suspeita de fraude."
        ),
        context=(
            "O bloqueio foi aplicado só pelo fluxo automatizado entre as instituições, "
            "sem conferência humana e sem que existisse qualquer reclamação contra a "
            "recebedora. A recebedora sustenta que o dinheiro é o pagamento de um serviço "
            "que prestou e que tem contrato e nota fiscal da venda."
        ),
        request=(
            "Sou a recebedora, fiquei sem acesso ao dinheiro que já era meu e quero "
            "contestar o bloqueio automático e pedir que uma pessoa do banco analise o "
            "caso."
        ),
        elicits=(
            ("contestation_right", "quero contestar o bloqueio automático"),
            (
                "contestation_channel",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "contestation_deadline",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            ("human_review", "pedir que uma pessoa do banco analise o caso"),
            (
                "reviewer_authority",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "review_outcome_communicated",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
        ),
        reference_answer=(
            "- Direito de contestar: você pode contestar o bloqueio automático do valor "
            "recebido e o pedido de devolução aberto contra a sua conta.\n"
            "- Canal de contestação: abra a contestação pela ouvidoria "
            "(ouvidoria@banco.com.br) ou pelo telefone do atendimento antifraude.\n"
            "- Prazo: a contestação pode ser apresentada em até 10 dias, a contar do "
            "bloqueio.\n"
            "- Revisão humana: um analista humano da área antifraude vai reavaliar o "
            "pedido de devolução e os documentos da venda que você apresentar.\n"
            "- Poderes do revisor: esse analista pode manter ou reverter o bloqueio e "
            "liberar o valor retido na sua conta.\n"
            "- Resultado: você será informada do resultado da revisão e do motivo dele."
        ),
        held_out=True,
        provenance=(
            "generated (uv run python tools/generate_brazil_scenarios.py): "
            "task=contestation_review; domain=credit; variant=pix_block_contest; "
            "anchor=Res. BCB 103/2021 (Pix — Mecanismo Especial de Devolução)"
        ),
    ),
    ContestationScenario(
        id="performance_ranking_contest",
        domain="employment",
        decision=(
            "O desligamento foi decidido a partir do ranqueamento automático de "
            "desempenho da equipe, sem parecer de nenhum gestor."
        ),
        context=(
            "O ranqueamento foi produzido inteiramente por um sistema que agrega metas "
            "mensais e registros de produtividade. O empregado sustenta que ficou dois "
            "meses afastado por licença médica e que o período entrou no cálculo como "
            "produção zero."
        ),
        request=(
            "Sou o empregado desligado e quero contestar o resultado desse ranqueamento e "
            "pedir que um gestor humano reveja a minha situação."
        ),
        elicits=(
            ("contestation_right", "quero contestar o resultado desse ranqueamento"),
            (
                "contestation_channel",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "contestation_deadline",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            ("human_review", "pedir que um gestor humano reveja a minha situação"),
            (
                "reviewer_authority",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "review_outcome_communicated",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
        ),
        reference_answer=(
            "- Direito de contestar: você pode contestar o resultado do ranqueamento e o "
            "desligamento decidido a partir dele.\n"
            "- Canal de contestação: registre a contestação pelo canal interno de "
            "recursos ou pelo e-mail do comitê de pessoas (recursos@empresa.com.br).\n"
            "- Prazo: você tem 10 dias, a contar desta comunicação, para apresentar a "
            "contestação.\n"
            "- Revisão humana: um gestor humano, e não o sistema, vai reavaliar o seu "
            "desempenho no período.\n"
            "- Poderes do revisor: esse gestor pode manter ou reverter o resultado e "
            "determinar o recálculo do período de licença médica.\n"
            "- Resultado: você será informado do resultado da revisão e das razões dele."
        ),
        held_out=False,
        provenance=(
            "generated (uv run python tools/generate_brazil_scenarios.py): "
            "task=contestation_review; domain=employment; "
            "variant=performance_ranking_contest; anchor=LGPD Art. 20; PL 2338/2023 Art. "
            "6"
        ),
    ),
    ContestationScenario(
        id="public_competition_titles_contest",
        domain="employment",
        decision=(
            "A pontuação da prova de títulos do concurso público foi atribuída por um "
            "sistema automatizado, que desconsiderou dois certificados enviados."
        ),
        context=(
            "A conferência dos títulos foi feita só pelo sistema, que leu os arquivos "
            "enviados e comparou com a tabela do edital. A candidata sustenta que os dois "
            "certificados desconsiderados atendem ao que o edital pede e que ficou fora "
            "da lista de classificados por 0,5 ponto."
        ),
        request=(
            "Sou a candidata e quero contestar a pontuação atribuída pelo sistema e pedir "
            "que uma pessoa da banca confira os meus títulos."
        ),
        elicits=(
            ("contestation_right", "quero contestar a pontuação atribuída pelo sistema"),
            (
                "contestation_channel",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "contestation_deadline",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            ("human_review", "pedir que uma pessoa da banca confira os meus títulos"),
            (
                "reviewer_authority",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "review_outcome_communicated",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
        ),
        reference_answer=(
            "- Direito de contestar: você pode contestar a pontuação atribuída pelo "
            "sistema na prova de títulos.\n"
            "- Canal de contestação: apresente o recurso exclusivamente pelo formulário "
            "eletrônico da área do candidato; conforme o edital, a banca não recebe "
            "recurso por e-mail, por correio nem presencialmente.\n"
            "- Prazo: o recurso deve ser apresentado em até 2 dias úteis, contados do "
            "primeiro dia útil seguinte ao da publicação do resultado.\n"
            "- Revisão humana: um examinador humano da banca vai reavaliar os "
            "certificados desconsiderados.\n"
            "- Poderes do revisor: esse examinador pode manter ou reverter a pontuação e "
            "recolocar a candidatura na lista de classificados.\n"
            "- Resultado: você será informada do resultado da revisão e da fundamentação "
            "dela."
        ),
        held_out=True,
        provenance=(
            "generated (uv run python tools/generate_brazil_scenarios.py): "
            "task=contestation_review; domain=employment; "
            "variant=public_competition_titles_contest; anchor=LGPD Art. 20; PL 2338/2023 "
            "Art. 6"
        ),
    ),
    ContestationScenario(
        id="bpc_suspension_contest",
        domain="social_benefit",
        decision=(
            "O pagamento do Benefício de Prestação Continuada foi suspenso "
            "automaticamente depois de uma revisão feita por cruzamento de bases."
        ),
        context=(
            "O cruzamento automático entre o Cadastro Único e o CNIS apontou uma renda "
            "que a beneficiária sustenta nunca ter recebido. Nenhum servidor examinou o "
            "caso antes do corte do pagamento."
        ),
        request=(
            "Sou a beneficiária, fiquei sem o benefício de um mês para o outro e quero "
            "contestar a suspensão e pedir que um servidor humano reveja o meu caso."
        ),
        elicits=(
            ("contestation_right", "quero contestar a suspensão"),
            (
                "contestation_channel",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "contestation_deadline",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            ("human_review", "pedir que um servidor humano reveja o meu caso"),
            (
                "reviewer_authority",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "review_outcome_communicated",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
        ),
        reference_answer=(
            "- Direito de contestar: você pode apresentar defesa contra a suspensão do "
            "benefício e contestar a renda que o cruzamento apontou.\n"
            "- Canal de contestação: apresente a defesa pelo Meu INSS, pela Central 135 "
            "ou numa Agência da Previdência Social, guardando o número do protocolo; se a "
            "suspensão for mantida, cabe recurso à Junta de Recursos do CRPS pelos mesmos "
            "canais.\n"
            "- Prazo: a defesa pode ser apresentada em até 30 dias, a contar do corte do "
            "pagamento.\n"
            "- Revisão humana: um servidor humano vai reavaliar o cruzamento e os "
            "documentos que você apresentar.\n"
            "- Poderes do revisor: esse servidor pode manter ou reverter a suspensão e "
            "restabelecer o pagamento.\n"
            "- Resultado: você será informada do resultado da revisão e das razões dele."
        ),
        held_out=False,
        provenance=(
            "generated (uv run python tools/generate_brazil_scenarios.py): "
            "task=contestation_review; domain=social_benefit; "
            "variant=bpc_suspension_contest; anchor=LGPD Art. 20; PL 2338/2023 Art. 6"
        ),
    ),
    ContestationScenario(
        id="housing_allocation_contest",
        domain="social_benefit",
        decision=(
            "A família ficou fora da lista de habilitados do programa habitacional por "
            "causa da pontuação calculada automaticamente pelo sistema de priorização."
        ),
        context=(
            "A pontuação foi gerada só pelo sistema, a partir dos dados do cadastro "
            "habitacional, sem conferência de nenhum servidor. A requerente sustenta que "
            "a condição de pessoa com deficiência do filho, que pontua no programa, não "
            "entrou no cálculo."
        ),
        request=(
            "Sou a requerente e quero contestar a pontuação atribuída à minha família e "
            "pedir que uma pessoa revise o cadastro e o cálculo."
        ),
        elicits=(
            ("contestation_right", "quero contestar a pontuação atribuída à minha família"),
            (
                "contestation_channel",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "contestation_deadline",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            ("human_review", "pedir que uma pessoa revise o cadastro e o cálculo"),
            (
                "reviewer_authority",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "review_outcome_communicated",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
        ),
        reference_answer=(
            "- Direito de contestar: você pode contestar a pontuação atribuída à sua "
            "família e a exclusão da lista de habilitados.\n"
            "- Canal de contestação: registre a contestação no atendimento do programa "
            "habitacional ou pelo e-mail da secretaria (habitacao@municipio.gov.br).\n"
            "- Prazo: a contestação pode ser apresentada em até 15 dias, a contar da "
            "publicação da lista.\n"
            "- Revisão humana: um servidor humano vai reavaliar o cadastro e refazer o "
            "cálculo.\n"
            "- Poderes do revisor: esse servidor pode manter ou reverter a pontuação e "
            "reposicionar a família na lista.\n"
            "- Resultado: você será informada do resultado da revisão e da fundamentação "
            "dela."
        ),
        held_out=True,
        provenance=(
            "generated (uv run python tools/generate_brazil_scenarios.py): "
            "task=contestation_review; domain=social_benefit; "
            "variant=housing_allocation_contest; anchor=LGPD Art. 20; PL 2338/2023 Art. 6"
        ),
    ),
    ContestationScenario(
        id="demonetization_contest",
        domain="content_moderation",
        decision=(
            "A monetização do canal foi desativada automaticamente por um classificador "
            "que marcou os vídeos como conteúdo impróprio para anunciantes."
        ),
        context=(
            "A desativação foi aplicada só pelo classificador, sem revisão de nenhum "
            "analista. O criador sustenta que os vídeos marcados são reportagens sobre um "
            "tema sensível e que não violam as regras de conteúdo da plataforma."
        ),
        request=(
            "Sou o criador do canal, perdi a minha principal fonte de renda e quero "
            "contestar a desativação e pedir que um analista humano reveja os vídeos."
        ),
        elicits=(
            ("contestation_right", "quero contestar a desativação"),
            (
                "contestation_channel",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "contestation_deadline",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            ("human_review", "pedir que um analista humano reveja os vídeos"),
            (
                "reviewer_authority",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "review_outcome_communicated",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
        ),
        reference_answer=(
            "- Direito de contestar: você pode contestar a desativação da monetização do "
            "canal.\n"
            "- Canal de contestação: abra a contestação pelo formulário do painel do "
            "criador ou pelo e-mail de suporte (suporte@plataforma.com.br).\n"
            "- Prazo: você tem 30 dias, a contar deste aviso, para apresentar a "
            "contestação.\n"
            "- Revisão humana: um analista humano, e não o classificador, vai reavaliar "
            "os vídeos marcados.\n"
            "- Poderes do revisor: esse analista pode manter ou reverter a desativação e "
            "restabelecer a monetização.\n"
            "- Resultado: você será informado do resultado da revisão e do motivo dele."
        ),
        held_out=False,
        provenance=(
            "generated (uv run python tools/generate_brazil_scenarios.py): "
            "task=contestation_review; domain=content_moderation; "
            "variant=demonetization_contest; anchor=LGPD Art. 20; PL 2338/2023 Art. 6"
        ),
    ),
    ContestationScenario(
        id="marketplace_delisting_contest",
        domain="content_moderation",
        decision=(
            "Os anúncios da loja foram retirados do ar automaticamente por um sistema que "
            "classificou os produtos como possivelmente falsificados."
        ),
        context=(
            "A retirada foi decidida só pelo sistema de detecção do marketplace, sem "
            "conferência humana. A vendedora sustenta que tem nota fiscal de todos os "
            "produtos e que a marca é licenciada para revenda."
        ),
        request=(
            "Sou a vendedora e quero contestar a retirada dos meus anúncios e pedir que "
            "uma pessoa analise as notas fiscais que enviei."
        ),
        elicits=(
            ("contestation_right", "quero contestar a retirada dos meus anúncios"),
            (
                "contestation_channel",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "contestation_deadline",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            ("human_review", "pedir que uma pessoa analise as notas fiscais que enviei"),
            (
                "reviewer_authority",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
            (
                "review_outcome_communicated",
                "(enquadramento da tarefa — nenhum trecho do cenário licencia este elemento)"
            ),
        ),
        reference_answer=(
            "- Direito de contestar: você pode contestar a retirada dos anúncios e a "
            "classificação dos produtos.\n"
            "- Canal de contestação: registre a contestação pelo painel do vendedor ou "
            "pelo e-mail de integridade (integridade@marketplace.com.br).\n"
            "- Prazo: a contestação pode ser apresentada em até 15 dias, a contar da "
            "retirada dos anúncios.\n"
            "- Revisão humana: um analista humano vai reavaliar as notas fiscais e a "
            "licença de revenda da marca.\n"
            "- Poderes do revisor: esse analista pode manter ou reverter a retirada e "
            "republicar os anúncios.\n"
            "- Resultado: você será informada do resultado da revisão e da fundamentação "
            "dela."
        ),
        held_out=True,
        provenance=(
            "generated (uv run python tools/generate_brazil_scenarios.py): "
            "task=contestation_review; domain=content_moderation; "
            "variant=marketplace_delisting_contest; anchor=LGPD Art. 20; PL 2338/2023 "
            "Art. 6"
        ),
    ),
]
