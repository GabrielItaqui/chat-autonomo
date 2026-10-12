"""Portão de testes: se algo falhar, a publicação não acontece."""
import os, re, sys, py_compile
import yaml

CORES = ["azul", "verde", "vermelho", "laranja", "roxo", "grafite"]
PROVEDORES = ["gemini", "openrouter", "anthropic", "openai"]
erros = []

def erro(msg):
    erros.append(msg)

# T1
try:
    with open("config.yml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError("o arquivo está vazio ou mal formado")
except Exception as e:
    print(f"❌ T1: config.yml inválido ({e}). Confira espaços e indentação (nunca use Tab).")
    sys.exit(1)

# T2
for campo in ["nome", "descricao", "tema", "prompt_sistema"]:
    if not str(cfg.get(campo) or "").strip():
        erro(f"T2: o campo '{campo}' está vazio ou ausente no config.yml.")

# T3
tema = str(cfg.get("tema") or "").lower()
cores = [c.strip() for c in tema.split(" e ") if c.strip()]
if not (1 <= len(cores) <= 2) or any(c not in CORES for c in cores):
    erro(f"T3: tema '{cfg.get('tema')}' inválido. Use uma ou duas cores de: {', '.join(CORES)} (ex.: 'azul e vermelho').")

# T4
if len(str(cfg.get("prompt_sistema") or "").strip()) < 80:
    erro("T4: prompt_sistema precisa ter pelo menos 80 caracteres.")

# T4b
prov = cfg.get("provedores")
if not isinstance(prov, dict) or not prov:
    erro("T4b: 'provedores' precisa ter ao menos um item (gemini, openrouter, anthropic ou openai).")
else:
    for p, m in prov.items():
        if p not in PROVEDORES:
            erro(f"T4b: provedor '{p}' não existe. Use: {', '.join(PROVEDORES)}.")
        if not str(m or "").strip():
            erro(f"T4b: o provedor '{p}' está sem modelo.")

# T5
logo = str(cfg.get("logo") or "").strip()
if logo and not logo.startswith("https://"):
    if not logo.lower().endswith(".svg"):
        erro("T5: a logo precisa ser .svg (ou um link https). PNG/JPG são recusados pelo Hugging Face.")
    elif not os.path.isfile(logo):
        erro(f"T5: o arquivo de logo '{logo}' não está no repositório.")
alt = cfg.get("logo_altura", 56)
if not isinstance(alt, int) or not (32 <= alt <= 160):
    erro("T5: logo_altura deve ser um número entre 32 e 160.")

# T6
try:
    py_compile.compile("app.py", doraise=True)
except Exception as e:
    erro(f"T6: app.py tem erro de sintaxe: {e}")

# T7
padrao = re.compile(r"(sk-or-[A-Za-z0-9\-]{10,}|sk-ant-[A-Za-z0-9\-_]{10,}|sk-proj-[A-Za-z0-9\-_]{10,}|hf_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9\-_]{30,})")
for raiz, dirs, arquivos in os.walk("."):
    dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
    for nome in arquivos:
        if nome == "testes.py":
            continue
        caminho = os.path.join(raiz, nome)
        try:
            with open(caminho, encoding="utf-8") as f:
                if padrao.search(f.read()):
                    erro(f"T7: parece haver uma chave de API em '{caminho}'. Remova e REVOGUE a chave.")
        except (UnicodeDecodeError, OSError):
            pass

if erros:
    print("❌ Publicação bloqueada. Corrija:\n")
    for e in erros:
        print(" -", e)
    sys.exit(1)
print("✅ Liberado para publicar")
