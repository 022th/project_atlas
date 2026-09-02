import threading


class Categorizer:
    """
    Detecta o tema/projeto de uma conversa usando a própria LLM.
    Roda em background (thread separada) para não atrasar a resposta.

    Fluxo:
    1. Pega a lista de projetos existentes no banco.
    2. Pede ao LLM: "Qual projeto essa conversa pertence? Se nenhum se encaixa, sugira um novo."
    3. Salva o projeto na conversa e atualiza o checkpoint.
    """

    def __init__(self, memory, openrouter_client):
        self.memory = memory
        self.client = openrouter_client

    def categorize_in_background(self, conversation_id, user_input, troy_output):
        """Lança a categorização numa thread separada. Não bloqueia o loop principal."""
        thread = threading.Thread(
            target=self._do_categorize,
            args=(conversation_id, user_input, troy_output),
            daemon=True,
        )
        thread.start()

    def _do_categorize(self, conversation_id, user_input, troy_output):
        """Executa a categorização e atualiza o banco."""
        try:
            # 1. Pega projetos existentes
            existing = self.memory.get_all_projects()

            # 2. Pede ao LLM para identificar o tema
            project = self._detect_project(user_input, troy_output, existing)

            if not project:
                return  # conversa casual, sem projeto

            # 3. Atualiza a conversa com o projeto detectado
            self.memory.update_conversation_project(conversation_id, project)

            # 4. Atualiza o checkpoint do projeto
            self.memory.save_checkpoint(
                project=project,
                summary=self._make_summary(user_input, troy_output),
                where_we_stopped=troy_output[:200],
            )
        except Exception as e:
            # Background — não pode crashar o programa principal
            print(f"\n[categorizer] erro: {e}")

    def _detect_project(self, user_input, troy_output, existing_projects):
        """Usa o LLM para detectar o projeto/tema da conversa."""
        projects_list = ", ".join(existing_projects) if existing_projects else "nenhum ainda"

        prompt = f"""Analise essa conversa e identifique o TEMA/PROJETO principal.

Projetos que já existem no banco: [{projects_list}]

Conversa:
User: {user_input}
Troy: {troy_output[:300]}

Regras:
1. Se a conversa pertence a um projeto existente, responda EXATAMENTE o nome dele.
2. Se é um tema novo, crie um nome curto em minúsculo com hífen (ex: "sim-racing", "ingles", "fivem-scripts").
3. Se é conversa casual sem tema claro (saudação, pergunta aleatória), responda exatamente: NENHUM
4. Responda APENAS o nome do projeto, nada mais. Sem explicação, sem pontuação extra."""

        messages = [
            {"role": "system", "content": "Você classifica conversas em projetos/temas. Responda apenas o nome do projeto."},
            {"role": "user", "content": prompt},
        ]

        response = self.client.chat(messages, max_tokens=30, temperature=0.1)

        if not response or "❌" in response:
            return None

        project = response.strip().lower().strip('"').strip("'").strip(".")

        if project == "nenhum" or len(project) > 40:
            return None

        return project

    def _make_summary(self, user_input, troy_output):
        """Cria um resumo curto da conversa para o checkpoint."""
        # Versão simples: usa o input do usuário como resumo
        # Futuramente pode usar LLM pra gerar algo melhor
        return user_input[:100]

    def detect_project_sync(self, user_input):
        """
        Detecção síncrona rápida: checa se o input do usuário menciona
        algum projeto existente. Usado ANTES de responder para puxar o checkpoint.
        Não usa LLM — apenas busca textual nos nomes de projetos existentes.
        """
        existing = self.memory.get_all_projects()
        input_lower = user_input.lower()

        for project in existing:
            # Checa se o nome do projeto aparece no input
            if project.lower() in input_lower:
                return project

            # Checa variações sem hífen
            project_words = project.lower().replace("-", " ").split()
            if all(word in input_lower for word in project_words):
                return project

        return None
