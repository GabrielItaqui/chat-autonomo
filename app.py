import os, html, base64
import yaml
import gradio as gr

# ZeroGPU exige ao menos uma função @spaces.GPU. No computador o pacote não existe.
try:
    import spaces
except ImportError:
    class spaces:
        @staticmethod
        def GPU(fn=None, **_):
            return fn if fn else (lambda f: f)

@spaces.GPU(duration=1)
def gpu_minima():  # só para o ZeroGPU aceitar o Space; nunca é chamada
    return None

with open("config.yml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

NOME = CFG["nome"]
DESCRICAO = CFG["descricao"]
PROMPT = CFG["prompt_sistema"]
MAX_TOKENS = int(CFG.get("max_tokens", 800))
PROVEDORES = CFG["provedores"]
EXEMPLOS = CFG.get("exemplos") or []
ALTURA = int(CFG.get("logo_altura", 56))

CORES = {"azul": "#1F4E9C", "verde": "#1E7B4F", "vermelho": "#B3261E",
         "laranja": "#C25E00", "roxo": "#6A3FA0", "grafite": "#2F3640"}
nomes = [c.strip().lower() for c in str(CFG["tema"]).split(" e ")]
COR1 = CORES[nomes[0]]
COR2 = CORES[nomes[1]] if len(nomes) > 1 else COR1

CHAVES = {"gemini": "GEMINI_API_KEY",
          "openrouter": "OPENROUTER_API_KEY",
          "anthropic": "ANTHROPIC_API_KEY",
          "openai": "OPENAI_API_KEY"}

# ---------- provedores ----------
def via_gemini(modelo, msgs):
    from openai import OpenAI
    c = OpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
               api_key=os.environ[CHAVES["gemini"]])
    fluxo = c.chat.completions.create(
        model=modelo, messages=msgs, max_tokens=MAX_TOKENS, stream=True,
        reasoning_effort="none")  # evita que o "pensar" gaste o max_tokens (modelos Flash)
    for ev in fluxo:
        if ev.choices and ev.choices[0].delta.content:
            yield ev.choices[0].delta.content

def via_openrouter(modelo, msgs):
    from openai import OpenAI
    c = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ[CHAVES["openrouter"]])
    fluxo = c.chat.completions.create(
        model=modelo, messages=msgs, max_tokens=MAX_TOKENS, stream=True,
        extra_body={"reasoning": {"enabled": False}})
    for ev in fluxo:
        if ev.choices and ev.choices[0].delta.content:
            yield ev.choices[0].delta.content

def via_anthropic(modelo, msgs):
    import anthropic
    c = anthropic.Anthropic(api_key=os.environ[CHAVES["anthropic"]])
    conversa = [m for m in msgs if m["role"] != "system"]
    with c.messages.stream(model=modelo, max_tokens=MAX_TOKENS,
                           system=PROMPT, messages=conversa) as s:
        for t in s.text_stream:
            yield t

def via_openai(modelo, msgs):
    from openai import OpenAI
    c = OpenAI(api_key=os.environ[CHAVES["openai"]])
    fluxo = c.chat.completions.create(
        model=modelo, messages=msgs, max_completion_tokens=MAX_TOKENS, stream=True)
    for ev in fluxo:
        if ev.choices and ev.choices[0].delta.content:
            yield ev.choices[0].delta.content

FUNCOES = {"gemini": via_gemini, "openrouter": via_openrouter, "anthropic": via_anthropic, "openai": via_openai}

# ---------- chat ----------
def responder(mensagem, historico):
    msgs = [{"role": "system", "content": PROMPT}]
    for m in historico:  # o modelo não tem memória: reenviamos tudo
        if isinstance(m.get("content"), str) and m["role"] in ("user", "assistant"):
            msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": mensagem})

    ativos = [(p, m) for p, m in PROVEDORES.items() if os.environ.get(CHAVES.get(p, ""))]
    if not ativos:
        yield ("⚠️ Nenhuma chave de API configurada. No Hugging Face, abra o Space → "
               "Settings → Variables and secrets → New secret e cadastre "
               "GEMINI_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY ou OPENAI_API_KEY. "
               "Depois reinicie o Space.")
        return

    erros = []
    for p, modelo in ativos:
        texto = ""
        try:
            for pedaco in FUNCOES[p](modelo, msgs):
                texto += pedaco
                yield texto
            if texto:
                return
            erros.append(f"**{p}** ({modelo}): resposta vazia")
        except Exception as e:
            if texto:
                yield texto + f"\n\n⚠️ A resposta foi interrompida ({p}): {e}"
                return
            erros.append(f"**{p}** ({modelo}): {e}")
    yield "😕 Não consegui responder agora. Motivo de cada tentativa:\n\n" + "\n\n".join(f"- {e}" for e in erros)

# ---------- visual ----------
def logo_html():
    logo = str(CFG.get("logo") or "").strip()
    if not logo:
        return ""
    if logo.startswith("https://"):
        src = logo
    elif os.path.isfile(logo):
        with open(logo, "rb") as f:
            src = "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()
    else:
        return ""
    return f'<img src="{src}" style="height:{ALTURA}px" alt="logo">'

CSS = """
.gradio-container {background: linear-gradient(135deg, COR1, COR2) !important; min-height: 100vh;}
#topo {text-align:center; color:#fff; padding:24px 12px 8px;}
#topo h1 {color:#fff; margin:8px 0 4px; font-size:2rem;}
#topo p {color:rgba(255,255,255,.92); margin:0;}
#cartao {background:#fff; border-radius:16px; padding:12px; max-width:900px;
         margin:0 auto; box-shadow:0 8px 30px rgba(0,0,0,.25);}
""".replace("COR1", COR1).replace("COR2", COR2)

with gr.Blocks(css=CSS, title=NOME) as demo:
    gr.HTML(f'<div id="topo">{logo_html()}<h1>{html.escape(NOME)}</h1>'
            f'<p>{html.escape(DESCRICAO)}</p></div>')
    with gr.Group(elem_id="cartao"):
        gr.ChatInterface(responder, type="messages",
                         examples=EXEMPLOS or None, cache_examples=False)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
