import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from database import init_db, db
from models import Usuario, Canal, Favorito, Progresso
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Troque em produção
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Funções auxiliares para carregar JSON ----------
def carregar_json_no_banco():
    if Canal.query.first() is not None:
        logger.info("Banco já contém dados. Nenhuma carga realizada.")
        return

    json_dir = 'm3u'
    json_path = os.path.join(json_dir, 'lista.json')
    if not os.path.exists(json_path):
        logger.warning(f"Arquivo {json_path} não encontrado.")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except Exception as e:
        logger.error(f"Erro ao ler JSON: {e}")
        return

    if not isinstance(dados, list):
        logger.error("Formato JSON inválido: esperava uma lista.")
        return

    for item in dados:
        nome = item.get('nome', '')
        logo = item.get('logo', '')
        tipo_original = item.get('tipo', '')
        categoria = item.get('categoria', '')
        temporada = item.get('temporada')
        episodio = item.get('episodio')
        url = item.get('url', '')

        if tipo_original.lower() == 'radio':
            tipo = 'radio'
        elif tipo_original.lower() == 'series':
            tipo = 'serie'
        elif tipo_original.lower() == 'filmes':
            tipo = 'filme'
        else:
            tipo = 'tv'

        canal = Canal(
            nome=nome,
            url=url,
            logo=logo,
            grupo='',
            tvg_id='',
            tipo=tipo,
            categoria=categoria,
            temporada=temporada if temporada is not None else None,
            episodio=episodio if episodio is not None else None
        )
        if tipo == 'serie':
            import re
            match = re.search(r'S(\d+)E(\d+)', nome, re.IGNORECASE)
            if match:
                canal.serie_nome = re.sub(r'S\d+E\d+', '', nome, flags=re.IGNORECASE).strip()
            else:
                canal.serie_nome = nome
        db.session.add(canal)

    db.session.commit()
    logger.info(f"{len(dados)} itens carregados do JSON.")

# ---------- Rotas principais ----------
@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            return redirect(url_for('index'))
        return render_template('login.html', erro='Email ou senha inválidos')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        if Usuario.query.filter_by(email=email).first():
            return render_template('register.html', erro='Email já cadastrado')
        hash_senha = generate_password_hash(senha)
        usuario = Usuario(nome=nome, email=email, senha=hash_senha)
        db.session.add(usuario)
        db.session.commit()
        session['usuario_id'] = usuario.id
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    return redirect(url_for('login'))

@app.route('/tv')
def tv():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('tv.html')

@app.route('/series')
def series():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('series.html')

@app.route('/filmes')
def filmes():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('filmes.html')

@app.route('/radio')
def radio():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('radio.html')

@app.route('/serie/<nome>')
def serie_detalhe(nome):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    episodios = Canal.query.filter_by(tipo='serie', serie_nome=nome).order_by(
        Canal.temporada, Canal.episodio).all()
    temporadas = {}
    for ep in episodios:
        temp = ep.temporada
        if temp not in temporadas:
            temporadas[temp] = []
        temporadas[temp].append(ep)
    return render_template('series-detalhe.html', serie_nome=nome, temporadas=temporadas)

@app.route('/filme/<int:id>')
def filme_detalhe(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    filme = Canal.query.get_or_404(id)
    return render_template('filme-detalhe.html', filme=filme)

@app.route('/play/<int:id>')
def play(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    canal = Canal.query.get_or_404(id)
    return render_template('player.html', canal=canal)

@app.route('/favoritos')
def favoritos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario_id = session['usuario_id']
    favs = Favorito.query.filter_by(usuario_id=usuario_id).all()
    return render_template('favoritos.html', favoritos=favs)

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    return render_template('perfil.html', usuario=usuario)

@app.route('/busca')
def busca():
    termo = request.args.get('q', '')
    return render_template('resultados.html', termo=termo)

# ---------- API ----------
def get_random_items(tipo, limite=8):
    from sqlalchemy.sql.expression import func
    return Canal.query.filter_by(tipo=tipo).order_by(func.random()).limit(limite).all()

def get_recentemente_assistidos(usuario_id, limite=8):
    progressos = Progresso.query.filter_by(usuario_id=usuario_id).order_by(Progresso.data_atualizacao.desc()).limit(limite).all()
    return [p.canal for p in progressos if p.canal]

@app.route('/api/inicio')
def api_inicio():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    usuario_id = session['usuario_id']
    filmes_rec = [c.serialize() for c in get_random_items('filme', 8)]
    series_rec = [c.serialize() for c in get_random_items('serie', 8)]
    recentes = [c.serialize() for c in get_recentemente_assistidos(usuario_id, 8)]
    return jsonify({
        'filmes_recomendados': filmes_rec,
        'series_recomendadas': series_rec,
        'assistido_recentemente': recentes
    })

@app.route('/api/filmes/categoria/<categoria>')
def api_filmes_categoria(categoria):
    filmes = Canal.query.filter_by(tipo='filme', categoria=categoria).limit(8).all()
    return jsonify([f.serialize() for f in filmes])

@app.route('/api/filmes/lancamento')
def api_filmes_lancamento():
    filmes = Canal.query.filter_by(tipo='filme').order_by(Canal.id.desc()).limit(8).all()
    return jsonify([f.serialize() for f in filmes])

@app.route('/api/filmes/lista')
def api_filmes_lista():
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 10
    filmes = Canal.query.filter_by(tipo='filme').order_by(Canal.nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [f.serialize() for f in filmes.items],
        'total': filmes.total,
        'pagina': pagina,
        'total_paginas': filmes.pages
    })

@app.route('/api/series/categoria/<categoria>')
def api_series_categoria(categoria):
    series = Canal.query.filter_by(tipo='serie', categoria=categoria).limit(8).all()
    return jsonify([s.serialize() for s in series])

@app.route('/api/series/lancamento')
def api_series_lancamento():
    series = Canal.query.filter_by(tipo='serie').order_by(Canal.id.desc()).limit(8).all()
    return jsonify([s.serialize() for s in series])

@app.route('/api/series/lista')
def api_series_lista():
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 10
    subquery = db.session.query(Canal.serie_nome, db.func.min(Canal.id).label('id')).filter_by(tipo='serie').group_by(Canal.serie_nome).subquery()
    series = db.session.query(Canal).join(subquery, Canal.id == subquery.c.id).order_by(Canal.serie_nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [s.serialize() for s in series.items],
        'total': series.total,
        'pagina': pagina,
        'total_paginas': series.pages
    })

@app.route('/api/tv/lista')
def api_tv_lista():
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 10
    canais = Canal.query.filter_by(tipo='tv').order_by(Canal.nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [c.serialize() for c in canais.items],
        'total': canais.total,
        'pagina': pagina,
        'total_paginas': canais.pages
    })

@app.route('/api/radio/lista')
def api_radio_lista():
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 10
    radios = Canal.query.filter_by(tipo='radio').order_by(Canal.nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [r.serialize() for r in radios.items],
        'total': radios.total,
        'pagina': pagina,
        'total_paginas': radios.pages
    })

@app.route('/api/busca')
def api_busca():
    termo = request.args.get('q', '').strip()
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 20

    if not termo:
        return jsonify({'itens': [], 'total': 0, 'pagina': 1, 'total_paginas': 1})

    query = Canal.query.filter(Canal.nome.ilike(f'%{termo}%'))
    total = query.count()
    paginacao = query.order_by(Canal.nome).paginate(page=pagina, per_page=por_pagina, error_out=False)

    return jsonify({
        'itens': [c.serialize() for c in paginacao.items],
        'total': total,
        'pagina': pagina,
        'total_paginas': paginacao.pages
    })

# ---------- Favoritos ----------
@app.route('/favoritar/<int:canal_id>', methods=['POST'])
def favoritar(canal_id):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    usuario_id = session['usuario_id']
    existe = Favorito.query.filter_by(usuario_id=usuario_id, canal_id=canal_id).first()
    if existe:
        db.session.delete(existe)
        db.session.commit()
        return jsonify({'status': 'removido'})
    else:
        canal = Canal.query.get(canal_id)
        fav = Favorito(usuario_id=usuario_id, canal_id=canal_id, tipo=canal.tipo)
        db.session.add(fav)
        db.session.commit()
        return jsonify({'status': 'adicionado'})

@app.route('/api/favoritos')
def api_favoritos():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    usuario_id = session['usuario_id']
    favs = Favorito.query.filter_by(usuario_id=usuario_id).all()
    return jsonify([f.canal.serialize() for f in favs if f.canal])

# ---------- Progresso ----------
@app.route('/progresso/<int:canal_id>', methods=['POST'])
def salvar_progresso(canal_id):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    data = request.get_json()
    tempo = data.get('tempo')
    duracao = data.get('duracao')
    usuario_id = session['usuario_id']
    progresso = Progresso.query.filter_by(usuario_id=usuario_id, canal_id=canal_id).first()
    if progresso:
        progresso.tempo = tempo
        progresso.duracao = duracao
        progresso.data_atualizacao = datetime.utcnow()
    else:
        progresso = Progresso(usuario_id=usuario_id, canal_id=canal_id, tempo=tempo, duracao=duracao)
        db.session.add(progresso)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/progresso/<int:canal_id>', methods=['GET'])
def obter_progresso(canal_id):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    usuario_id = session['usuario_id']
    progresso = Progresso.query.filter_by(usuario_id=usuario_id, canal_id=canal_id).first()
    if progresso:
        return jsonify({'tempo': progresso.tempo, 'duracao': progresso.duracao})
    return jsonify({'tempo': 0, 'duracao': 0})

# ---------- Proxy ----------
@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    if not url:
        return 'URL não fornecida', 400
    headers = {}
    if 'Range' in request.headers:
        headers['Range'] = request.headers.get('Range')
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=10)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items() if name.lower() not in excluded_headers]
        return Response(resp.iter_content(chunk_size=8192), status=resp.status_code, headers=headers)
    except Exception as e:
        return f'Erro no proxy: {str(e)}', 500

if __name__ == '__main__':
    with app.app_context():
        carregar_json_no_banco()
    app.run(debug=True)