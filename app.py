from flask import Flask, render_template_string, request, jsonify
import requests
from bs4 import BeautifulSoup
import random
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
        // Formata e interpreta valores em pt-BR
        function parsePreco(valor) {
            if (!valor) return null;
            let v = String(valor).replace(/[R$\s]/g, "").trim();
            if (!v) return null;
            if (v.includes(",")) {
                v = v.replace(/\./g, "").replace(",", ".");
            } else {
                const partes = v.split(".");
                if (partes.length === 2 && partes[1].length <= 2) {
                    v = partes[0] + "." + partes[1];
                } else {
                    v = v.replace(/\./g, "");
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
            if (n != null) {
                el.value = formatarPreco(n);
            }
        }

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

                // Detecta o maior e o menor para montar "De:" e "Por só:" corretamente
                let de = "";
                let por = formatarPreco(precoNum);
                if (precoAntigoNum != null) {
                    if (precoAntigoNum > precoNum) {
                        de = formatarPreco(precoAntigoNum);
                    } else if (precoNum > precoAntigoNum) {
                        de = formatarPreco(precoNum);
                        por = formatarPreco(precoAntigoNum);
                    } else {
                        de = formatarPreco(precoAntigoNum);
                    }
                }

                if (de) texto += `❌ De: ${de}\\n`;
                texto += `✅ Por só: ${por}`;
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
    "mixer": [
        "Sopa, vitamina ou bolo, o mixer resolve tudo na cozinha. 🥣😄",
        "Bater, triturar, misturar sem esforço? Mixer é vida! 🥤"
    ],
    "memoria": [
        "Seu PC engasga com 40 abas abertas? 🧠😄",
        "Computador lento? Uma memória nova resolve!"
    ],
    "memória": [
        "Seu PC engasga com 40 abas abertas? 🧠😄",
        "Computador lento? Uma memória nova resolve!"
    ],
    "ram": [
        "Seu PC engasga com 40 abas abertas? 🧠😄"
    ],
    "ssd": [
        "PC lento é igual a fila de banco: ninguém merece. 💻😄",
        "Ligar o PC e esperar 10 minutos? SSD novo resolve!"
    ],
    "hd": [
        "PC lento é igual a fila de banco: ninguém merece. 💻😄",
        "Chega de esperar o Windows carregar! 💽"
    ],
    "placa de video": [
        "Jogar no low é sofrência. 🎮😅 Placa de vídeo nova é alegria!",
        "PC pra rodar tudo no ultra? Só com essa placa! 🎮"
    ],
    "placa de vídeo": [
        "Jogar no low é sofrência. 🎮😅 Placa de vídeo nova é alegria!",
        "PC pra rodar tudo no ultra? Só com essa placa! 🎮"
    ],
    "maquina de lavar": [
        "Roupa suja acumulando? Essa máquina dá conta da bagunça. 👕😄"
    ],
    "lava e seca": [
        "Roupa suja acumulando? Essa lava e seca dá conta da bagunça. 👕😄"
    ],
    "tanquinho": [
        "Lavar roupa na mão é coisa do passado! 🧺😄"
    ],
    "processador": [
        "Bater, triturar, misturar sem esforço? Processador resolve! 🥤"
    ],
    "espremedor": [
        "Suco natural sem esforço? 🍊 Espremedor resolve!"
    ],
    "poltrona": [
        "Sua coluna agradece uma poltrona nova! 🪑😌"
    ],
    "sofa": [
        "Sofá novo, vida nova! 🛋️😄"
    ],
    "sofá": [
        "Sofá novo, vida nova! 🛋️😄"
    ],
    "mesa": [
        "Mesa nova deixa o home office até mais produtivo! 🖥️😄"
    ],
    "cama": [
        "Dormir mal é coisa do passado! 🛏️😄"
    ],
    "colchao": [
        "Sua coluna merece um colchão melhor! 😴"
    ],
    "armario": [
        "Organização é tudo, né? 🗄️😄"
    ],
    "estante": [
        "Livros e decoração pedem uma estante nova! 📚😄"
    ],
    "ducha": [
        "Banho de hotel todo dia? 🚿 Ducha nova resolve!"
    ],
    "camera": [
        "Fotografar como profissional? 📸 Essa câmera te leva lá!"
    ],
    "filmadora": [
        "Registrar momentos sem tremer? 🎥 Essa filmadora resolve!"
    ],
    "drone": [
        "Ver o mundo de cima é outro nível! 🚁😎"
    ],
    "gopro": [
        "Aventura merece registro profissional! 📹😄"
    ],
    "bike": [
        "Pedalar sem esforço e com estilo? 🚴‍♂️ Essa bike é sucesso!"
    ],
    "bicicleta": [
        "Pedalar sem esforço e com estilo? 🚴‍♂️ Essa bike é sucesso!"
    ],
    "patinete": [
        "Mobilidade rápida e sem trânsito! 🛴😄"
    ],
    "skate": [
        "Radical de fininho! 🛹😎"
    ],
    "carrinho de bebe": [
        "Passear com o bebê ficou fácil! 👶🛒"
    ],
    "cadeirinha": [
        "Segurança e conforto para o pequeno! 👶🚗"
    ],
    "babador": [
        "Hora da papinha sem bagunça! 👶🍼"
    ],
    "cachorro": [
        "Seu pet merece o melhor! 🐶😍"
    ],
    "gato": [
        "Seu gato vai aprovar essa! 🐱😍"
    ],
    "pet": [
        "Seu pet vai amar! 🐾😍"
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
    if not titulo:
        return random.choice(FALLBACK)

    titulo_lower = titulo.lower()
    for categoria, piadas in PIADAS.items():
        if categoria in titulo_lower:
            return random.choice(piadas)

    # Geração dinâmica com o nome do produto para cobrir qualquer categoria
    nome_produto = titulo.strip()
    if len(nome_produto) > 60:
        nome_produto = nome_produto[:57].rstrip() + "..."
    padroes_dinamicos = [
        "Já pensou em dar um up na sua vida com um {prod}? 😄",
        "Seu {prod} já deu o que tinha que dar? Hora de trocar! 😅",
        "Cansado de sofrer com o {prod}? Esse aqui resolve! 🎯",
        "Achou o {prod} perfeito? Corre que é promoção! 🏃‍♂️",
        "Vai deixar essa oferta de {prod} passar? 😱",
        "Promoção boa de {prod} é assim: chega calada e some rápido! ⏰",
    ]
    return random.choice(padroes_dinamicos).format(prod=nome_produto)


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
    # Mercado Livre: /nome-do-produto/p/MLB123456
    m = re.search(r"/([^/?#]+)/p/(?:MLB|MLM|MLA|MCO|MLU)\d+", url)
    if m:
        slug = m.group(1).replace("-", " ").strip()
        if len(slug) > 3:
            return slug
    # Magazine Luiza / Shopee: /nome-do-produto/p/hash
    m = re.search(r"/([^/?#]+)/p/[a-z0-9]{6,}", url)
    if m:
        slug = m.group(1).replace("-", " ").strip()
        if len(slug) > 3:
            return slug
    return None


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
        "magalu": ["h1", "h1[data-testid='heading-product-title']"],
        "amazon": ["#productTitle", "h1"],
        "shopee": ["h1"],
    }
    for s in seletores.get(loja, ["h1"]):
        el = soup.select_one(s)
        if el:
            titulo = limpar_titulo(el.get_text(strip=True))
            if titulo:
                return titulo
    return None


def limpar_titulo(texto):
    if not texto:
        return None
    texto = re.sub(r"\s+", " ", texto).strip()
    sufixos = [
        "| Mercado Livre", "no Mercado Livre", "em Promoção | Mercado Livre",
        "| Amazon.com.br", "| Amazon", "| Magazine Luiza", "| Shopee Brasil",
        "| Shopee", "| MercadoLivre", "| Mercado Libre",
    ]
    for suf in sufixos:
        if texto.lower().endswith(suf.lower()):
            texto = texto[: -len(suf)].strip()
            break
    # Ignora títulos típicos de página de perfil/compartilhamento
    marcadores = ["compartilhou", "divulgou", "recomendou", "recomendações"]
    tl = texto.lower()
    if any(m in tl for m in marcadores):
        return None
    if len(texto) < 3:
        return None
    return texto


@app.route("/buscar-titulo", methods=["POST"])
def buscar_titulo():
    try:
        dados = request.json
        url = dados.get("url")
        loja = dados.get("loja", "magalu")

        if not url:
            return jsonify({"titulo": None, "erro": "URL não fornecida"})

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }

        # Segue redirects (links de afiliado/encurtados) e pega a URL final
        resposta = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        soup = BeautifulSoup(resposta.text, "html.parser")
        url_final = resposta.url
        url_canonica = extrair_url_canonica(soup, url_final)

        # Mercado Livre: se acharmos o ID do produto, buscamos a página limpa
        # (evita cair na página de perfil/indicação do link de afiliado)
        if loja == "mercadolivre":
            ml_id = extrair_id_ml(url) or extrair_id_ml(url_final) or extrair_id_ml(url_canonica)
            if ml_id:
                try:
                    r2 = requests.get(
                        f"https://www.mercadolivre.com.br/p/{ml_id}",
                        headers=headers, timeout=20, allow_redirects=True
                    )
                    soup = BeautifulSoup(r2.text, "html.parser")
                    url_final = r2.url
                    url_canonica = extrair_url_canonica(soup, url_final)
                except Exception:
                    pass

        titulo = None

        # 1) Nome do produto a partir do slug da URL (não depende de perfil)
        titulo = titulo_do_slug(url_canonica) or titulo_do_slug(url_final)

        # 2) Meta tags og:title / twitter:title (mais confiáveis que <title>)
        if not titulo:
            titulo = extrair_meta_titulo(soup)

        # 3) Título (h1) específico do produto por loja
        if not titulo:
            titulo = extrair_h1_produto(soup, loja)

        # 4) Tag <title>, com limpeza de sufixo e filtro de perfil
        if not titulo:
            raw = soup.title.get_text(strip=True) if soup.title else None
            titulo = limpar_titulo(raw)

        # 5) Última tentativa: slug da URL colada originalmente
        if not titulo:
            titulo = titulo_do_slug(url)

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
