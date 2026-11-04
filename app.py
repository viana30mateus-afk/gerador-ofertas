from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
import random
import traceback

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
        .btn-piada {
            background: #fff; color: #128c7e; border: 1px solid #128c7e;
            margin-top: 8px; padding: 8px; font-size: 14px; cursor: pointer;
        }
        .btn-piada:hover { background: #f0f7f5; }
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
        <div class="info">Preencha manualmente ou deixe em branco para buscar automaticamente.</div>

        <label>Piadinha / introdução</label>
        <textarea id="piada" placeholder="Deixe em branco para gerar automaticamente 😉"></textarea>
        <button type="button" class="btn-piada" onclick="gerarPiada()">🎲 Gerar piada automática</button>

        <label>Preço atual *</label>
        <input type="text" id="preco" placeholder="R$ 370,64">

        <label>Preço antigo (opcional)</label>
        <input type="text" id="preco_antigo" placeholder="R$ 499,90">

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
        let mensagemFinal = "";

        async function buscarTitulo() {
            const url = document.getElementById("url").value.trim();
            if (!url) {
                mostrarErro("Cole o link do produto primeiro para buscar o título");
                return null;
            }
            try {
                const res = await fetch("/buscar-titulo", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url, loja: document.getElementById("loja").value })
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

        async function gerarPiada() {
            let titulo = document.getElementById("titulo").value.trim();
            if (!titulo) {
                titulo = await buscarTitulo();
            }
            if (!titulo) {
                titulo = "produto";
            }
            try {
                const res = await fetch("/gerar-piada", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ titulo })
                });
                const data = await res.json();
                if (data.piada) {
                    document.getElementById("piada").value = data.piada;
                    return data.piada;
                }
            } catch (e) {
                console.log("Erro ao gerar piada:", e);
            }
            return "";
        }

        async function gerar() {
            document.getElementById("erro").style.display = "none";
            document.getElementById("resultado").style.display = "none";
            document.getElementById("btnCopiar").style.display = "none";
            document.getElementById("btnWhats").style.display = "none";

            const url = document.getElementById("url").value.trim();
            const loja = document.getElementById("loja").value;
            const tituloManual = document.getElementById("titulo").value.trim();
            let piada = document.getElementById("piada").value.trim();
            const preco = document.getElementById("preco").value.trim();
            const precoAntigo = document.getElementById("preco_antigo").value.trim();
            const cupom = document.getElementById("cupom").value.trim();

            if (!url) {
                mostrarErro("Por favor, cole o link do produto");
                return;
            }
            if (!preco) {
                mostrarErro("Por favor, informe o preço atual");
                return;
            }

            document.getElementById("loading").style.display = "block";

            let titulo = tituloManual;
            if (!titulo) {
                titulo = await buscarTitulo();
            }

            // Gera piada automaticamente se o campo estiver vazio
            if (!piada) {
                piada = await gerarPiada();
            }

            document.getElementById("loading").style.display = "none";

            try {
                let texto = "";
                if (piada) texto += piada + "\\n\\n";
                if (titulo) texto += titulo + "\\n";
                if (precoAntigo) texto += `❌ De: ${precoAntigo}\\n`;
                texto += `✅ Por só: ${preco}`;
                if (loja === "amazon") texto += " no Programe e Poupe";
                texto += "\\n";
                if (cupom) texto += `🎟️ Cupom: ${cupom}\\n`;
                texto += `🛒 Link: ${url}`;

                mensagemFinal = texto;

                document.getElementById("resultado").style.display = "block";
                document.getElementById("resultado").textContent = texto;
                document.getElementById("btnCopiar").style.display = "block";
                document.getElementById("btnWhats").style.display = "block";
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
            const url = "https://wa.me/?text=" + encodeURIComponent(mensagemFinal);
            window.open(url, "_blank");
        }
    </script>
</body>
</html>
"""

# Categorias de piadas baseadas em palavras-chave do título
PIADAS = {
    "microondas": [
        "Esquentar a marmita em 2 minutos virou rotina? 🍱😄",
        "Sua marmita merece um upgrade de chef! 🍲",
        "Cansado de comer comida fria? 🔥 Esse resolve!"
    ],
    "celular": [
        "Seu celular tá pedindo aposentadoria? 📱 Para de sofrer e troca logo!",
        "Tela trincada é igual dor de dente: só piora. 😅 Melhor trocar!",
        "Quer um celular que não descarrega no meio do dia? ⚡ Bora!"
    ],
    "smartphone": [
        "Seu smartphone virou peso de papel? 📱 Hora de dar adeus!",
        "Sabe aquele app que não abre? Pois é, ele também merece descanso. 😂"
    ],
    "fone": [
        "Fugir do barulho sem sair do sofá? 🎧 Agora dá!",
        "Seu fone só funciona de um lado? 😅 Chega de viver pela metade!",
        "Música boa merece som de verdade! 🎶"
    ],
    "tv": [
        "Maratonar série sem sair da cama? 📺 Só se for com essa!",
        "Sua TV parece rádio? Hora do upgrade! 📺😄"
    ],
    "televis": [
        "Maratonar série sem sair da cama? 📺 Só se for com essa!"
    ],
    "geladeira": [
        "Sua comida merece um 5 estrelas! 🧊 Geladeira nova, vida nova.",
        "Geladeira velha é igual ex: dá saudade até lembrar dos problemas. 😅"
    ],
    "refrigerador": [
        "Seu refrigerador tá fazendo barulho de trator? 🚜 Hora de trocar!"
    ],
    "lavadora": [
        "Cansei de lavar roupa na mão? 🧺 Sua lavadora nova chegou!",
        "Roupa limpa sem esforço é luxo? 🧺 Não mais!"
    ],
    "lavar": [
        "Lavar roupa na mão é coisa do passado! 🧺😄"
    ],
    "ar condicionado": [
        "Verão tá chegando... 🥵 Não derreta, se refresque!",
        "Dormir no calor é tortura! ❄️ Resolve isso agora."
    ],
    "climatizador": [
        "Verão tá chegando... 🥵 Não derreta, se refresque!"
    ],
    "notebook": [
        "Seu notebook tá mais lento que tartaruga? 💻 Hora de acelerar!",
        "Abrir o navegador e travar? 😅 Nunca mais!"
    ],
    "laptop": [
        "Seu laptop tá mais lento que tartaruga? 💻 Hora de acelerar!"
    ],
    "air fryer": [
        "Fritar sem culpa e sem óleo? 🍟 Air fryer resolve!",
        "Batata crocante sem se lambuzar? 🍟 Só vem!"
    ],
    "fritadeira": [
        "Fritar sem culpa e sem óleo? 🍟 Fritadeira resolve!"
    ],
    "cafeteira": [
        "Acordar sem café é missão impossível? ☕ Seu salvador chegou!",
        "Café passado na hora, sem sair de casa! ☕😍"
    ],
    "cafe": [
        "Café ruim é pior que segunda-feira! ☕ Resolva isso!"
    ],
    "smartwatch": [
        "Quer estilo e saúde no pulso? ⌚ Bora!",
        "Seu pulso merece companhia inteligente! ⌚😎"
    ],
    "relogio": [
        "Quer estilo e saúde no pulso? ⌚ Bora!"
    ],
    "aspirador": [
        "Limpar a casa sem levantar do sofá? 🤖 Robô aspirador é vida!",
        "Poeira tem prazo de validade! 🧹"
    ],
    "robo": [
        "Limpar a casa sem levantar do sofá? 🤖 Robô aspirador é vida!"
    ],
    "cooktop": [
        "Cozinha de chef sem virar mestre-cuca? 🍳 Esse cooktop te salva!"
    ],
    "fogao": [
        "Seu fogão tá mais velho que sua playlist? 😅 Hora de trocar!"
    ],
    "frigideira": [
        "Ovo que não gruda é paz de espírito! 🍳😄"
    ],
    "panela": [
        "Panela velha é igual namoro ruim: só decepção. 😅"
    ],
    "liquidificador": [
        "Vitamina sem caroço e sem drama? 🥤 Liquidificador novo resolve!"
    ],
    "batedeira": [
        "Bolo fofo sem suar a camisa? 🎂 Só com essa!"
    ],
    "ventilador": [
        "Calor tá brabo? 🥵 Ventilador novo é sobrevivência!"
    ],
    "chuveiro": [
        "Banho frio no inverno? 🚿 Jamais! Troca logo esse chuveiro."
    ],
    "cadeira": [
        "Sua coluna agradece uma cadeira nova! 🪑😌"
    ],
    "mouse": [
        "Mouse que pula igual saci? 🖱️ Hora de aposentar!"
    ],
    "teclado": [
        "Teclado com tecla que não responde? ⌨️ Chega de sofrer!"
    ],
    "monitor": [
        "Monitor pequeno é igual cineminha de bolso! 🖥️ Amplia essa visão!"
    ],
}

FALLBACK = [
    "Achou que ia pagar caro? 😂 Olha essa oferta!",
    "Promoção boa é assim: chega calada e some rápido! 🏃‍♂️",
    "Se você tá vendo isso, é porque ainda dá tempo! ⏰",
    "O bolso agradece, o desejo também! 😍",
    "Oferta que não dá pra ignorar! 👀",
]


def gerar_piada(titulo):
    titulo_lower = titulo.lower()
    for categoria, piadas in PIADAS.items():
        if categoria in titulo_lower:
            return random.choice(piadas)
    return random.choice(FALLBACK)


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/buscar-titulo", methods=["POST"])
def buscar_titulo():
    try:
        dados = request.json
        url = dados.get("url")
        loja = dados.get("loja", "magalu")

        if not url:
            return jsonify({"titulo": None, "erro": "URL não fornecida"})

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resposta = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resposta.text, "html.parser")

        titulo = None
        for seletor in ["h1", "title", "#productTitle", ".p-name"]:
            el = soup.select_one(seletor)
            if el:
                texto = el.get_text(strip=True)
                if texto and len(texto) > 5:
                    titulo = texto
                    break

        if titulo and len(titulo) > 200:
            titulo = titulo[:200] + "..."

        return jsonify({"titulo": titulo})
    except Exception as e:
        print(f"Erro ao buscar título: {traceback.format_exc()}")
        return jsonify({"titulo": None, "erro": str(e)})


@app.route("/gerar-piada", methods=["POST"])
def gerar_piada_route():
    try:
        dados = request.json
        titulo = dados.get("titulo", "")
        if not titulo:
            return jsonify({"piada": random.choice(FALLBACK)})
        piada = gerar_piada(titulo)
        return jsonify({"piada": piada})
    except Exception as e:
        print(f"Erro ao gerar piada: {traceback.format_exc()}")
        return jsonify({"piada": None, "erro": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
