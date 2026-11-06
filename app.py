from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
import traceback
import re

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gerador de Ofertas</title>
    <style>
        * { box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { background: #f0f2f5; padding: 20px; margin: 0; }
        .container { max-width: 500px; margin: 0 auto; background: white; padding: 25px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #25d366; font-size: 24px; margin-bottom: 5px; }
        p.subtitle { text-align: center; color: #666; font-size: 14px; margin-top: 0; margin-bottom: 25px; }
        label { display: block; margin-top: 15px; font-weight: 600; color: #333; font-size: 14px; }
        input, textarea, select, button {
            width: 100%; padding: 12px; margin-top: 6px;
            border: 1px solid #ddd; border-radius: 10px; font-size: 15px;
        }
        textarea { min-height: 80px; resize: vertical; }
        button {
            background: #25d366; color: white; border: none;
            font-weight: bold; cursor: pointer; margin-top: 20px;
        }
        button:hover { background: #1da851; }
        .secondary { background: #128c7e; margin-top: 10px; }
        .secondary:hover { background: #0d7065; }
        .resultado {
            margin-top: 20px; padding: 15px; background: #f8f9fa;
            border-radius: 10px; border-left: 4px solid #25d366;
            white-space: pre-wrap; display: none;
        }
        .loading { text-align: center; color: #666; display: none; margin-top: 15px; }
        .erro {
            margin-top: 15px; padding: 15px; background: #fee;
            border-radius: 10px; border-left: 4px solid #c33;
            color: #c33; display: none; font-size: 14px;
        }
        .info { font-size: 12px; color: #888; margin-top: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛒 Gerador de Ofertas</h1>
        <p class="subtitle">Cole o link e monte sua mensagem em segundos</p>

        <label>Link do produto *</label>
        <input type="url" id="url" placeholder="https://www.magazineluiza.com.br/..." oninput="detectarLoja()">
        <span id="lojaDetectada" style="font-size: 12px; color: #25d366; margin-top: 4px; display: none;"></span>

        <label>Loja</label>
        <select id="loja">
            <option value="auto">🔍 Detectar automaticamente</option>
            <option value="magalu">Magazine Luiza</option>
            <option value="mercadolivre">Mercado Livre</option>
            <option value="amazon">Amazon</option>
            <option value="shopee">Shopee</option>
            <option value="aliexpress">AliExpress</option>
        </select>

        <label>Título do produto</label>
        <input type="text" id="titulo" placeholder="Micro-ondas Philco 20L Branco">
        <div class="info">Preencha manualmente ou deixe em branco para buscar automaticamente.</div>

        <label>Preço atual *</label>
        <input type="text" id="preco" placeholder="Ex.: 370,64" onblur="formatarCampoPreco('preco')">

        <label>Preço antigo (opcional)</label>
        <input type="text" id="preco_antigo" placeholder="Ex.: 499,90" onblur="formatarCampoPreco('preco_antigo')">

        <label>Cupom de desconto (opcional)</label>
        <input type="text" id="cupom" placeholder="CUPOM10">

        <button onclick="gerar()">✨ Gerar mensagem</button>

        <div class="loading" id="loading">Buscando informações...</div>
        <div class="erro" id="erro"></div>
        <div class="resultado" id="resultado"></div>

        <button class="secondary" onclick="copiar()" style="display:none;" id="btnCopiar">📋 Copiar mensagem</button>
        <button class="secondary" onclick="enviarWhats()" style="display:none;" id="btnWhats">📲 Enviar pelo WhatsApp</button>
    </div>

    <script>
        function detectarLoja() {
            const url = document.getElementById("url").value.trim();
            const badge = document.getElementById("lojaDetectada");
            const select = document.getElementById("loja");

            if (!url) {
                badge.style.display = "none";
                return;
            }

            let loja = "";
            let cor = "";

            if (url.includes("mercadolivre.com.br") || url.includes("meli.la") || url.includes("mlb")) {
                loja = "Mercado Livre"; cor = "#ffe600"; select.value = "mercadolivre";
            } else if (url.includes("magazineluiza.com.br") || url.includes("magalu")) {
                loja = "Magazine Luiza"; cor = "#0086ff"; select.value = "magalu";
            } else if (url.includes("amazon.com.br")) {
                loja = "Amazon"; cor = "#ff9900"; select.value = "amazon";
            } else if (url.includes("shopee.com.br")) {
                loja = "Shopee"; cor = "#ee4d2d"; select.value = "shopee";
            } else if (url.includes("aliexpress.com")) {
                loja = "AliExpress"; cor = "#ff4747"; select.value = "aliexpress";
            }

            if (loja) {
                badge.textContent = "✓ " + loja + " detectada";
                badge.style.color = cor;
                badge.style.display = "block";
            } else {
                badge.style.display = "none";
            }
        }

        function parsePreco(valor) {
            if (!valor) return null;
            let v = String(valor).replace(/[R$\\s]/g, "").trim();
            if (!v) return null;
            if (v.includes(",")) {
                v = v.replace(/\\./g, "").replace(",", ".");
            } else {
                const partes = v.split(".");
                if (partes.length === 2 && partes[1].length <= 2) {
                    v = partes[0] + "." + partes[1];
                } else {
                    v = v.replace(/\\./g, "");
                }
            }
            const n = parseFloat(v);
            return isNaN(n) ? null : n;
        }

        function formatarPreco(n) {
            if (n == null || isNaN(n)) return "";
            return "R$ " + n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }

        function formatarCampoPreco(id) {
            const el = document.getElementById(id);
            const n = parsePreco(el.value);
            if (n != null) el.value = formatarPreco(n);
        }

        function limparPrecoTitulo(t) {
            if (!t) return t;
            return t.replace(/\\s*[-–—|:]?\\s*(por\\s+)?R\\$\\s*\\d[\\d.,]*.*$/i, "").trim();
        }

        let mensagemFinal = "";

        async function buscarTitulo() {
            const url = document.getElementById("url").value.trim();
            const loja = document.getElementById("loja").value;
            if (!url) {
                mostrarErro("Cole o link do produto primeiro para buscar o título");
                return null;
            }
            try {
                const res = await fetch("/buscar-titulo", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url, loja })
                });
                if (!res.ok) throw new Error("Erro ao buscar título: " + res.status);
                const data = await res.json();
                if (data.titulo) {
                    document.getElementById("titulo").value = data.titulo;
                    return data.titulo;
                }
            } catch (e) {
                console.log("Não foi possível buscar título automaticamente:", e);
            }
            return null;
        }

        async function gerar() {
            document.getElementById("erro").style.display = "none";
            document.getElementById("resultado").style.display = "none";
            document.getElementById("btnCopiar").style.display = "none";
            document.getElementById("btnWhats").style.display = "none";

            const url = document.getElementById("url").value.trim();
            let loja = document.getElementById("loja").value;
            const tituloManual = document.getElementById("titulo").value.trim();
            const precoTexto = document.getElementById("preco").value.trim();
            const precoAntigoTexto = document.getElementById("preco_antigo").value.trim();
            const cupom = document.getElementById("cupom").value.trim();

            if (!url) { mostrarErro("Por favor, cole o link do produto"); return; }
            if (!precoTexto) { mostrarErro("Por favor, informe o preço atual"); return; }

            const precoNum = parsePreco(precoTexto);
            const precoAntigoNum = parsePreco(precoAntigoTexto);

            if (precoNum == null) {
                mostrarErro("Preço atual inválido. Use formato como 370,64 ou 370.64");
                return;
            }

            document.getElementById("loading").style.display = "block";

            let titulo = tituloManual;
            if (!titulo) titulo = await buscarTitulo();

            document.getElementById("loading").style.display = "none";

            try {
                let texto = "";
                titulo = limparPrecoTitulo(titulo);
                if (titulo) texto += titulo + "\\n";

                let menor = precoNum;
                let maior = null;
                if (precoAntigoNum != null) {
                    maior = Math.max(precoNum, precoAntigoNum);
                    menor = Math.min(precoNum, precoAntigoNum);
                }

                if (maior != null) texto += "❌ De: " + formatarPreco(maior) + "\\n";
                texto += "✅ Por só: " + formatarPreco(menor);
                if (loja === "amazon") texto += " no Programe e Poupe";
                texto += "\\n";
                if (cupom) texto += "🎟️ Cupom: " + cupom + "\\n";
                texto += "🛒 Link: " + url;

                mensagemFinal = texto;

                document.getElementById("resultado").style.display = "block";
                document.getElementById("resultado").textContent = texto;
                document.getElementById("btnCopiar").style.display = "block";
                document.getElementById("btnWhats").style.display = "block";

                document.getElementById("url").value = "";
                document.getElementById("titulo").value = "";
                document.getElementById("preco").value = "";
                document.getElementById("preco_antigo").value = "";
                document.getElementById("cupom").value = "";
                document.getElementById("loja").value = "auto";
                document.getElementById("lojaDetectada").style.display = "none";
            } catch (e) {
                mostrarErro("Erro ao gerar mensagem: " + e.message);
            }
        }

        function mostrarErro(msg) {
            const erroDiv = document.getElementById("erro");
            erroDiv.textContent = "⚠️ " + msg;
            erroDiv.style.display = "block";
        }

        function copiar() {
            navigator.clipboard.writeText(mensagemFinal)
                .then(() => alert("✅ Mensagem copiada!"))
                .catch(() => alert("❌ Erro ao copiar. Tente selecionar o texto manualmente."));
        }

        function enviarWhats() {
            window.open("https://wa.me/?text=" + encodeURIComponent(mensagemFinal), "_blank");
        }
    </script>
</body>
</html>
"""


def detectar_loja(url):
    if not url:
        return "magalu"
    u = url.lower()
    if "mercadolivre.com.br" in u or "meli.la" in u or "mlb" in u:
        return "mercadolivre"
    elif "magazineluiza.com.br" in u or "magalu" in u:
        return "magalu"
    elif "amazon.com.br" in u:
        return "amazon"
    elif "shopee.com.br" in u:
        return "shopee"
    elif "aliexpress.com" in u:
        return "aliexpress"
    return "magalu"


@app.route("/")
def index():
    return render_template_string(HTML)


def extrair_url_canonica(soup, url_atual):
    el = soup.find("link", rel="canonical")
    if el and el.get("href"):
        return el["href"]
    return url_atual


def extrair_id_ml(url):
    if not url:
        return None
    m = re.search(r"/(MLB|MLM|MLA|MCO|MLU)\d+", url)
    return m.group(0).replace("/", "") if m else None


def titulo_do_slug(url):
    if not url:
        return None
    padroes = [
        r"/([^/?#]+)/p/(?:MLB|MLM|MLA|MCO|MLU)\d+",  # Mercado Livre
        r"/([^/?#]+)/p/[a-z0-9]{6,}",                # Magalu / Shopee
        r"/item/([^/?#]+)\.html",                    # AliExpress
    ]
    for p in padroes:
        m = re.search(p, url)
        if m:
            slug = m.group(1).replace("-", " ").strip()
            if len(slug) > 3:
                return slug
    return None


def limpar_preco_do_titulo(titulo):
    """Remove 'R$ 999,00' (e tudo depois) do título."""
    if not titulo:
        return titulo
    titulo = re.sub(r"\s*[-–—|:]?\s*(?:por\s+)?R\$\s*\d[\d.,]*.*$", "", titulo, flags=re.IGNORECASE)
    return titulo.strip(" -–—,:;·|")


def limpar_titulo(texto):
    if not texto:
        return None
    texto = re.sub(r"\s+", " ", texto).strip()
    sufixos = [
        "| Mercado Livre", "no Mercado Livre", "em Promoção | Mercado Livre",
        "| Amazon.com.br", "| Amazon", "| Magazine Luiza", "| Shopee Brasil",
        "| Shopee", "| MercadoLivre", "| Mercado Libre", "| AliExpress",
    ]
    for suf in sufixos:
        if texto.lower().endswith(suf.lower()):
            texto = texto[: -len(suf)].strip()
            break
    texto = limpar_preco_do_titulo(texto)
    marcadores = ["compartilhou", "divulgou", "recomendou", "recomendações"]
    if any(m in texto.lower() for m in marcadores):
        return None
    if len(texto) < 3:
        return None
    return texto


def extrair_meta_titulo(soup):
    for nome, valor in [("property", "og:title"), ("name", "twitter:title"),
                        ("property", "twitter:title"), ("name", "og:title")]:
        el = soup.find("meta", attrs={nome: valor})
        if el and el.get("content"):
            titulo = limpar_titulo(el["content"])
            if titulo:
                return titulo
    return None


def extrair_h1_produto(soup, loja):
    seletores = {
        "mercadolivre": ["h1.ui-pdp-title", "h1[itemprop='name']", "h1"],
        "magalu": ["h1[data-testid='heading-product-title']", "h1"],
        "amazon": ["#productTitle", "h1"],
        "shopee": ["h1"],
        "aliexpress": ["h1", ".product-title", ".product-name", "span.product-title-text"],
    }
    for s in seletores.get(loja, ["h1"]):
        el = soup.select_one(s)
        if el:
            titulo = limpar_titulo(el.get_text(strip=True))
            if titulo:
                return titulo
    return None


@app.route("/buscar-titulo", methods=["POST"])
def buscar_titulo():
    try:
        dados = request.json
        url = dados.get("url")
        loja = dados.get("loja", "auto")

        if not url:
            return jsonify({"titulo": None, "erro": "URL não fornecida"})

        if loja == "auto":
            loja = detectar_loja(url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }

        resposta = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        soup = BeautifulSoup(resposta.text, "html.parser")
        url_final = resposta.url
        url_canonica = extrair_url_canonica(soup, url_final)

        if loja == "mercadolivre":
            ml_id = extrair_id_ml(url) or extrair_id_ml(url_final) or extrair_id_ml(url_canonica)
            if ml_id:
                try:
                    r2 = requests.get(f"https://www.mercadolivre.com.br/p/{ml_id}",
                                      headers=headers, timeout=20, allow_redirects=True)
                    soup = BeautifulSoup(r2.text, "html.parser")
                    url_final = r2.url
                    url_canonica = extrair_url_canonica(soup, url_final)
                except Exception:
                    pass

        titulo = (
            titulo_do_slug(url_canonica)
            or titulo_do_slug(url_final)
            or extrair_meta_titulo(soup)
            or extrair_h1_produto(soup, loja)
            or limpar_titulo(soup.title.get_text(strip=True) if soup.title else None)
            or titulo_do_slug(url)
        )

        if titulo:
            titulo = limpar_preco_do_titulo(titulo)
            if len(titulo) > 200:
                titulo = titulo[:200] + "..."

        return jsonify({"titulo": titulo})
    except Exception as e:
        print(f"Erro ao buscar título: {traceback.format_exc()}")
        return jsonify({"titulo": None, "erro": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
