from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

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
        .info { font-size: 12px; color: #888; margin-top: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛒 Gerador de Ofertas</h1>
        <p class="subtitle">Cole o link e monte sua mensagem em segundos</p>

        <label>Link do produto</label>
        <input type="url" id="url" placeholder="https://www.magazineluiza.com.br/..." required>

        <label>Loja</label>
        <select id="loja">
            <option value="magalu">Magazine Luiza</option>
            <option value="mercadolivre">Mercado Livre</option>
            <option value="amazon">Amazon</option>
            <option value="shopee">Shopee</option>
        </select>

        <label>Título do produto</label>
        <input type="text" id="titulo" placeholder="Micro-ondas Philco 20L Branco">
        <div class="info">Preencha manualmente ou deixe em branco para tentar buscar automaticamente.</div>

        <label>Piadinha / introdução</label>
        <textarea id="piada" placeholder="Esquentar a marmita em 2 minutos virou rotina? 🍱😄"></textarea>

        <label>Preço atual</label>
        <input type="text" id="preco" placeholder="R$ 370,64">

        <label>Preço antigo (opcional)</label>
        <input type="text" id="preco_antigo" placeholder="R$ 499,90">

        <label>Cupom de desconto (opcional)</label>
        <input type="text" id="cupom" placeholder="CUPOM10">

        <button onclick="gerar()">✨ Gerar mensagem</button>

        <div class="loading" id="loading">Buscando informações...</div>

        <div class="resultado" id="resultado"></div>

        <button class="secondary" onclick="copiar()" style="display:none;" id="btnCopiar">📋 Copiar mensagem</button>
        <button class="secondary" onclick="enviarWhats()" style="display:none;" id="btnWhats">📲 Enviar pelo WhatsApp</button>
    </div>

    <script>
        let mensagemFinal = "";

        async function gerar() {
            const url = document.getElementById("url").value;
            const loja = document.getElementById("loja").value;
            const tituloManual = document.getElementById("titulo").value;
            const piada = document.getElementById("piada").value;
            const preco = document.getElementById("preco").value;
            const precoAntigo = document.getElementById("preco_antigo").value;
            const cupom = document.getElementById("cupom").value;

            if (!url) { alert("Coloque o link do produto"); return; }

            document.getElementById("loading").style.display = "block";

            let titulo = tituloManual;

            if (!titulo) {
                try {
                    const res = await fetch("/buscar-titulo", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ url, loja })
                    });
                    const data = await res.json();
                    if (data.titulo) titulo = data.titulo;
                } catch (e) {
                    console.log("Não foi possível buscar título automaticamente");
                }
            }

            document.getElementById("loading").style.display = "none";

            let texto = "";
            if (piada) texto += piada + "\n\n";
            if (titulo) texto += titulo + "\n";
            if (precoAntigo) texto += `❌ De: ${precoAntigo}\n`;
            if (preco) texto += `✅ Por só: ${preco}`;
            if (loja === "amazon") texto += " no Programe e Poupe";
            texto += "\n";
            if (cupom) texto += `🎟️ Cupom: ${cupom}\n`;
            texto += `🛒 Link: ${url}`;

            mensagemFinal = texto;

            document.getElementById("resultado").style.display = "block";
            document.getElementById("resultado").textContent = texto;
            document.getElementById("btnCopiar").style.display = "block";
            document.getElementById("btnWhats").style.display = "block";
        }

        function copiar() {
            navigator.clipboard.writeText(mensagemFinal).then(() => alert("Mensagem copiada!"));
        }

        function enviarWhats() {
            const url = "https://wa.me/?text=" + encodeURIComponent(mensagemFinal);
            window.open(url, "_blank");
        }
    </script>
</body>
</html>
"""

SELETORES = {
    "amazon": {
        "titulo": ["#productTitle", "h1"],
        "preco": [".a-price .a-offscreen", ".a-price-whole", "#priceblock_dealprice", "#priceblock_ourprice"]
    },
    "mercadolivre": {
        "titulo": ["h1"],
        "preco": [".andes-money-amount__fraction", ".ui-pdp-price__part"]
    },
    "magalu": {
        "titulo": ["h1"],
        "preco": [".price-value", "[data-testid='price-value']", ".p-price"]
    },
    "shopee": {
        "titulo": ["h1", "title"],
        "preco": [".flex.items-center ._5ExxR", ".pmm3Kz"]
    }
}

def buscar_por_seletores(soup, seletores):
    for s in seletores:
        el = soup.select_one(s)
        if el:
            texto = el.get_text(strip=True)
            if texto:
                return texto
    return None

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/buscar-titulo", methods=["POST"])
def buscar_titulo():
    dados = request.json
    url = dados.get("url")
    loja = dados.get("loja", "magalu")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resposta = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resposta.text, "html.parser")

        titulo = buscar_por_seletores(soup, SELETORES.get(loja, {}).get("titulo", ["h1"]))

        # Limpa título muito longo da Shopee
        if titulo and len(titulo) > 200:
            titulo = titulo[:200] + "..."

        return jsonify({"titulo": titulo})
    except Exception as e:
        return jsonify({"titulo": None, "erro": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
