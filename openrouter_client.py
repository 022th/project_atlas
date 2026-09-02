import requests
import re


class OmniRouter:
    """
    Roteador inteligente de modelos.
    Analisa a mensagem do usuário em <1ms e direciona para o pool ideal:
      FAST  → conversa casual, saudações, respostas curtas
      SMART → raciocínio, explicações, análises complexas
      CODE  → programação, scripts, debug, código
    Se todos os modelos do pool falharem, tenta o fallback universal.
    """

    # Padrões para detectar código / programação
    CODE_PATTERNS = re.compile(
        r'\b(código|code|script|função|function|debug|erro|bug|programar?|variável|'
        r'python|lua|javascript|js|html|css|c\+\+|java|sql|api|json|xml|'
        r'fivem|assetto|mod|plugin|servidor|server|banco de dados|database|'
        r'git|terminal|cmd|powershell|pip|npm|compilar|rodar|executar|'
        r'classe|class|import|def |print|return|if |for |while |'
        r'array|lista|dicionário|dict|loop|regex)\b',
        re.IGNORECASE
    )

    # Padrões para conversa casual / respostas curtas
    CASUAL_PATTERNS = re.compile(
        r'^(oi|olá|ola|hey|eai|e ai|fala|salve|bom dia|boa tarde|boa noite|'
        r'tudo bem|como vai|beleza|valeu|obrigado|obg|blz|flw|falou|'
        r'tchau|sair|ok|sim|não|nao|uhum|hm+|ah+|legal|massa|show|'
        r'qual seu nome|quem é você|me conta|o que você faz)\b',
        re.IGNORECASE
    )

    def __init__(self, api_key, pool_fast, pool_smart, pool_code, pool_fallback):
        self.api_key = api_key
        self.pools = {
            "fast": pool_fast,
            "smart": pool_smart,
            "code": pool_code,
        }
        self.pool_fallback = pool_fallback
        self.base_url = "https://openrouter.ai/api/v1"

        # Estatísticas simples (útil para debug)
        self.stats = {"fast": 0, "smart": 0, "code": 0, "fallback": 0}

    def classify(self, user_input):
        """
        Classifica a mensagem do usuário em uma categoria.
        Executa em <1ms (regex puro, sem IA).
        """
        text = user_input.strip()

        # 1. Mensagem muito curta (< 6 palavras) → provavelmente casual
        if len(text.split()) <= 5 and not self.CODE_PATTERNS.search(text):
            return "fast"

        # 2. Contém termos de código/programação?
        if self.CODE_PATTERNS.search(text):
            return "code"

        # 3. É saudação ou conversa casual?
        if self.CASUAL_PATTERNS.match(text):
            return "fast"

        # 4. Mensagem longa ou complexa → modelo forte
        if len(text.split()) > 15:
            return "smart"

        # 5. Default → smart (melhor errar por excesso de qualidade)
        return "smart"

    def chat(self, messages, max_tokens=500, temperature=0.7):
        """
        Classifica automaticamente e envia para o pool correto.
        Retorna (resposta_texto, categoria_usada).
        """
        # Extrai o último input do usuário para classificar
        user_msg = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_msg = msg["content"]
                break

        category = self.classify(user_msg)
        pool = self.pools[category]

        # Tenta os modelos do pool escolhido
        response = self._try_pool(pool, messages, max_tokens, temperature)

        if response:
            self.stats[category] += 1
            return response

        # Pool falhou → tenta fallback universal
        response = self._try_pool(self.pool_fallback, messages, max_tokens, temperature)
        if response:
            self.stats["fallback"] += 1
            return response

        return "❌ Todos os modelos falharam. Tente novamente em ~1 minuto."

    def _try_pool(self, models, messages, max_tokens, temperature):
        """Tenta cada modelo da lista em ordem. Retorna a resposta ou None."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for model in models:
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30,
                )

                if response.status_code == 429:
                    continue  # modelo lotado, tenta próximo

                if response.status_code >= 400:
                    continue  # erro qualquer, tenta próximo

                result = response.json()

                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    if content:
                        return content

            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError:
                continue
            except Exception:
                continue

        return None  # todos falharam

    def get_stats(self):
        """Retorna estatísticas de uso dos pools."""
        total = sum(self.stats.values())
        if total == 0:
            return "Nenhuma requisição ainda."
        lines = [f"Total: {total} requisições"]
        for cat, count in self.stats.items():
            pct = (count / total * 100) if total > 0 else 0
            lines.append(f"  {cat.upper()}: {count} ({pct:.0f}%)")
        return "\n".join(lines)
